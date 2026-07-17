import os
from collections.abc import Sequence

from ..models import RetrievedChunk

try:
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover - optional dep
    CrossEncoder = None


_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


class CrossEncoderReranker:

    def __init__(self, model_name: str | None = None, allow_download: bool | None = None, device: str | None = None) -> None:
        self.model_name = model_name or os.getenv("GEMPRF_ASSISTANT_RERANKER_MODEL", _DEFAULT_MODEL)
        self._allow_download = (
            allow_download
            if allow_download is not None
            else os.getenv("GEMPRF_ASSISTANT_RERANKER_ALLOW_DOWNLOAD", "").strip().lower() in {"1", "true", "yes"}
        )
        self._device = device or (os.getenv("GEMPRF_ASSISTANT_RERANKER_DEVICE") or None)
        self._model = None
        self._init_error: str | None = None
        self._tried_load = False

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
            ordered = sorted(candidates, key=lambda r: r.score, reverse=True)
            return list(ordered[:top_k] if top_k else ordered), False

        pairs = [(question, c.chunk.text) for c in candidates]
        try:
            scores = self._model.predict(pairs)
        except Exception as exc:  
            self._init_error = f"predict failed: {exc}"
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
    flag = os.getenv("GEMPRF_ASSISTANT_RERANKER_ENABLED", "1").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return None
    return CrossEncoderReranker()
