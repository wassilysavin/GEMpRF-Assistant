"""HTTP API for the assistant: one engine worker behind a bounded queue, per-IP rate limit, answer cache."""
import asyncio
import hashlib
import logging
import os
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .conversation import ConversationHistory

logger = logging.getLogger("gemprf_assistant.server")

_MAX_QUESTION_CHARS = 600
_MAX_HISTORY_TURNS = 8


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass
class ApiConfig:
    """Server knobs, all env-overridable (GEMPRF_ASSISTANT_API_*)."""

    queue_max: int = field(default_factory=lambda: _int_env("GEMPRF_ASSISTANT_API_QUEUE_MAX", 8))
    timeout_s: int = field(default_factory=lambda: _int_env("GEMPRF_ASSISTANT_API_TIMEOUT_S", 180))
    cache_size: int = field(default_factory=lambda: _int_env("GEMPRF_ASSISTANT_API_CACHE_SIZE", 256))
    rate_per_min: int = field(default_factory=lambda: _int_env("GEMPRF_ASSISTANT_API_RATE_PER_MIN", 10))
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.getenv(
                "GEMPRF_ASSISTANT_API_CORS", "https://gemprf.github.io,http://localhost:8000"
            ).split(",")
            if o.strip()
        )
    )


class Turn(BaseModel):
    question: str = Field(min_length=1, max_length=_MAX_QUESTION_CHARS)
    answer: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=_MAX_QUESTION_CHARS)
    history: list[Turn] = Field(default_factory=list, max_length=_MAX_HISTORY_TURNS)


class ChatResponse(BaseModel):
    answer: str
    status: str
    citations: list[dict]
    cached: bool = False
    elapsed_s: float


def _build_engine():
    # Imported lazily: pulls in weaviate/torch, and tests substitute a stub here.
    from .rag.engine import GraphRagEngine

    return GraphRagEngine()


class _RateLimiter:
    """Fixed-window-ish per-IP limiter: at most rate_per_min requests in any rolling 60s."""

    def __init__(self, rate_per_min: int) -> None:
        self.rate = rate_per_min
        self._hits: dict[str, deque[float]] = {}

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        hits = self._hits.setdefault(ip, deque())
        while hits and now - hits[0] > 60.0:
            hits.popleft()
        if len(self._hits) > 10_000:  # bound memory against IP churn
            self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] < 60.0}
            hits = self._hits.setdefault(ip, hits)
        if len(hits) >= self.rate:
            return False
        hits.append(now)
        return True


class _AnswerCache:
    """LRU over normalized question text; only history-free requests are cacheable."""

    def __init__(self, size: int) -> None:
        self.size = size
        self._items: OrderedDict[str, dict] = OrderedDict()

    @staticmethod
    def key(question: str) -> str:
        return " ".join(question.lower().split())

    def get(self, question: str) -> dict | None:
        k = self.key(question)
        if k in self._items:
            self._items.move_to_end(k)
            return self._items[k]
        return None

    def put(self, question: str, payload: dict) -> None:
        if self.size <= 0:
            return
        self._items[self.key(question)] = payload
        while len(self._items) > self.size:
            self._items.popitem(last=False)


def _client_ip(request: Request) -> str:
    # Caddy sits in front and sets X-Forwarded-For; fall back to the socket peer.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _qid(question: str) -> str:
    """Short stable id for logs so we never log question content."""
    return hashlib.sha256(question.encode()).hexdigest()[:8]


async def _engine_worker(app: FastAPI) -> None:
    loop = asyncio.get_running_loop()
    while True:
        payload, future = await app.state.queue.get()
        if future.cancelled():
            app.state.queue.task_done()
            continue
        try:
            result = await loop.run_in_executor(None, _run_ask, app.state.engine, payload)
            if not future.cancelled():
                future.set_result(result)
        except Exception as exc:  # engine failures must not kill the worker
            if not future.cancelled():
                future.set_exception(exc)
        finally:
            app.state.queue.task_done()


def _run_ask(engine, payload: ChatRequest) -> dict:
    history = None
    if payload.history:
        history = ConversationHistory(max_turns=_MAX_HISTORY_TURNS)
        for turn in payload.history:
            history.add(turn.question, turn.answer)
    return engine.ask_dict(payload.question, history=history)


def create_app() -> FastAPI:
    config = ApiConfig()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ready = False
        app.state.queue = asyncio.Queue(maxsize=config.queue_max)
        loop = asyncio.get_running_loop()
        logger.info("building engine (first boot ingests the corpus; this can take minutes)")
        app.state.engine = await loop.run_in_executor(None, _build_engine)
        worker = asyncio.create_task(_engine_worker(app))
        app.state.ready = True
        logger.info("engine ready")
        try:
            yield
        finally:
            worker.cancel()
            close = getattr(app.state.engine, "close", None)
            if close:
                close()

    app = FastAPI(title="GEM-pRF Assistant API", lifespan=lifespan)
    app.state.config = config
    limiter = _RateLimiter(config.rate_per_min)
    cache = _AnswerCache(config.cache_size)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    @app.get("/readyz")
    async def readyz() -> dict:
        if not app.state.ready:
            raise HTTPException(status_code=503, detail="engine loading")
        return {"ok": True, "queue_depth": app.state.queue.qsize()}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        if not app.state.ready:
            raise HTTPException(status_code=503, detail="engine loading", headers={"Retry-After": "60"})
        if not limiter.allow(_client_ip(request)):
            raise HTTPException(status_code=429, detail="rate limit exceeded", headers={"Retry-After": "60"})

        started = time.monotonic()
        qid = _qid(payload.question)

        if not payload.history:
            hit = cache.get(payload.question)
            if hit is not None:
                logger.info("chat qid=%s cache=hit elapsed=0.0", qid)
                return ChatResponse(**hit, cached=True, elapsed_s=0.0)

        future: asyncio.Future = asyncio.get_running_loop().create_future()
        try:
            app.state.queue.put_nowait((payload, future))
        except asyncio.QueueFull:
            raise HTTPException(status_code=503, detail="server busy, try again shortly", headers={"Retry-After": "30"})

        try:
            result = await asyncio.wait_for(future, timeout=config.timeout_s)
        except asyncio.TimeoutError:
            future.cancel()
            logger.warning("chat qid=%s timeout after %ss", qid, config.timeout_s)
            raise HTTPException(status_code=504, detail="answer generation timed out")
        except HTTPException:
            raise
        except Exception:
            logger.exception("chat qid=%s engine error", qid)
            raise HTTPException(status_code=500, detail="internal error")

        elapsed = round(time.monotonic() - started, 2)
        body = {
            "answer": result.get("answer", ""),
            "status": result.get("status", "unknown"),
            "citations": result.get("citations", []),
        }
        if not payload.history and body["answer"]:
            cache.put(payload.question, body)
        logger.info(
            "chat qid=%s status=%s cache=miss elapsed=%.2f queue=%d",
            qid, body["status"], elapsed, app.state.queue.qsize(),
        )
        return ChatResponse(**body, cached=False, elapsed_s=elapsed)

    return app
