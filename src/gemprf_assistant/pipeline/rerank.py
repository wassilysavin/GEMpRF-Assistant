from collections.abc import Sequence

from ..config import get_settings
from ..models import RetrievedChunk
from ..observability import get_logger

try:
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover - optional dep
    CrossEncoder = None


_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


class CrossEncoderReranker:

    def __init__(self, model_name: str | None = None, allow_download: bool | None = None, device: str | None = None) -> None:
        s = get_settings()
        self.model_name = model_name or s.reranker_model or _DEFAULT_MODEL
        self._allow_download = allow_download if allow_download is not None else s.reranker_allow_download
        self._device = device or s.reranker_device
        self._model = None
        self._init_error: str | None = None
        self._tried_load = False
        self._warned = False

    def _warn_degraded(self) -> None:
        """Rerank silently falling back to embedding order bit us in production once; say it out loud, once."""
        if not self._warned:
            get_logger(__name__).warning(
                "cross-encoder reranker unavailable (%s); falling back to embedding-score order",
                self._init_error or "model not loaded",
            )
            self._warned = True

    @property
    def available(self) -> bool:
        if self._tried_load:
            return self._model is not None
        self._load()
        return self._model is not None

    def _load(self) -> None:
        self._tried_load = True
        if CrossEncoder is None:
            self._init_error = "sentence-transformers not installed"
            return
        try:
            kwargs: dict[str, object] = {}
            if not self._allow_download:
                kwargs["local_files_only"] = True
            if self._device:
                kwargs["device"] = self._device
            self._model = CrossEncoder(self.model_name, **kwargs)
        except TypeError:
            # Older CrossEncoder versions reject local_files_only.
            try:
                fallback_kwargs = {"device": self._device} if self._device else {}
                self._model = CrossEncoder(self.model_name, **fallback_kwargs)
            except Exception as exc:
                self._init_error = f"{exc}"
                self._model = None
        except Exception as exc:
            self._init_error = f"{exc}"
            self._model = None

    def rerank(
        self,
        question: str,
        candidates: Sequence[RetrievedChunk],
        top_k: int | None = None,
    ) -> tuple[list[RetrievedChunk], bool]:
        """ Reorders retrieved chunks by relevance to the question using a cross-encoder model
        """
        if not candidates:
            return [], False
        if not self.available or self._model is None:
            self._warn_degraded()
            ordered = sorted(candidates, key=lambda r: r.score, reverse=True)
            return list(ordered[:top_k] if top_k else ordered), False

        pairs = [(question, c.chunk.text) for c in candidates]
        try:
            scores = self._model.predict(pairs)
        except Exception as exc:
            self._init_error = f"predict failed: {exc}"
            self._warn_degraded()
            ordered = sorted(candidates, key=lambda r: r.score, reverse=True)
            return list(ordered[:top_k] if top_k else ordered), False

        scored = [
            RetrievedChunk(
                chunk=c.chunk,
                score=c.score,
                rerank_score=float(s),
                parent_score=c.parent_score,
            )
            for c, s in zip(candidates, scores)
        ]
        scored.sort(key=lambda r: (r.rerank_score if r.rerank_score is not None else r.score), reverse=True)
        return scored[:top_k] if top_k else scored, True


def build_reranker() -> CrossEncoderReranker | None:
    if not get_settings().reranker_enabled:
        return None
    return CrossEncoderReranker()
