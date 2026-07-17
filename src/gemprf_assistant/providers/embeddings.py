"""Embedding-backend factory and implementations (sentence-transformers local, OpenAI-compatible remote)."""
from collections.abc import Sequence
from typing import Protocol

import numpy as np

from ..config import Settings, get_settings

try:
    from langchain_openai import OpenAIEmbeddings
except Exception:
    OpenAIEmbeddings = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


def _normalize_rows(vectors: Sequence[Sequence[float]]) -> np.ndarray:
    array = np.asarray(vectors, dtype=np.float32)
    if array.ndim == 1:
        array = array[None, :]
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return array / norms


class EmbeddingBackend(Protocol):

    backend_name: str

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        """Return one L2-normalised float32 vector per text in 'texts'."""
        ...


class SentenceTransformerEmbeddingBackend:

    def __init__(self, model_name: str, local_files_only: bool = False, settings: Settings | None = None) -> None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed.")
        s = settings or get_settings()
        self.backend_name = f"sentence-transformers:{model_name}"
        self._model = SentenceTransformer(model_name, local_files_only=local_files_only)
        # Instruction-tuned models (e5, bge-en) need a query/passage prefix;
        # env-configurable, auto-defaulted by family, empty for plain models.
        qp = s.embed_query_prefix
        dp = s.embed_doc_prefix
        ml = model_name.lower()
        if qp is None and dp is None:
            if "e5" in ml:
                qp, dp = "query: ", "passage: "
            elif "bge" in ml and "en" in ml:
                qp, dp = "Represent this sentence for searching relevant passages: ", ""
        self._query_prefix = qp or ""
        self._doc_prefix = dp or ""

    def _encode(self, texts: Sequence[str], prefix: str) -> np.ndarray:
        vectors = self._model.encode(
            [prefix + t for t in texts] if prefix else list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return _normalize_rows(vectors)

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        # Documents (chunks, sections, parameter specs) get the passage prefix.
        return self._encode(texts, self._doc_prefix)

    def embed_query(self, texts: Sequence[str]) -> np.ndarray:
        return self._encode(texts, self._query_prefix)


class OpenAIEmbeddingBackend:

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        if OpenAIEmbeddings is None:
            raise RuntimeError("langchain_openai is not available.")
        provider_name = "openai-compatible" if base_url else "openai"
        self.backend_name = f"{provider_name}:{model_name}"
        kwargs = {"model": model_name}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self._embeddings = OpenAIEmbeddings(**kwargs)

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self._embeddings.embed_documents(list(texts))
        return _normalize_rows(vectors)


def build_embedding_backend(settings: Settings | None = None) -> EmbeddingBackend:
    s = settings or get_settings()
    provider = s.embedding_provider

    if provider == "openai":
        return OpenAIEmbeddingBackend(model_name=s.openai_embedding_model)

    if provider == "xai":
        model_name = (s.xai_embedding_model or "").strip()
        if not model_name:
            raise RuntimeError(
                "Set 'GEMPRF_ASSISTANT_XAI_EMBEDDING_MODEL' to an embedding model available on your xAI account."
            )
        if not s.xai_api_key:
            raise RuntimeError("Set `XAI_API_KEY` to use xAI embeddings.")
        return OpenAIEmbeddingBackend(model_name=model_name, api_key=s.xai_api_key, base_url=s.xai_base_url)

    if provider in {"openai-compatible", "openai_compatible"}:
        if not (s.openai_compat_embedding_model and s.openai_compat_api_key and s.openai_compat_base_url):
            raise RuntimeError(
                "Set 'GEMPRF_ASSISTANT_OPENAI_COMPAT_EMBEDDING_MODEL', "
                "'GEMPRF_ASSISTANT_OPENAI_COMPAT_API_KEY', and 'GEMPRF_ASSISTANT_OPENAI_COMPAT_BASE_URL'."
            )
        return OpenAIEmbeddingBackend(
            model_name=s.openai_compat_embedding_model,
            api_key=s.openai_compat_api_key,
            base_url=s.openai_compat_base_url,
        )

    if provider in {"", "sentence-transformers", "sentence_transformers", "local"}:
        try:
            return SentenceTransformerEmbeddingBackend(
                model_name=s.embedding_model,
                local_files_only=not s.embedding_allow_download,
                settings=s,
            )
        except Exception as sentence_error:
            if s.xai_api_key and s.xai_embedding_model:
                return OpenAIEmbeddingBackend(
                    model_name=s.xai_embedding_model, api_key=s.xai_api_key, base_url=s.xai_base_url
                )
            if s.openai_api_key:
                return OpenAIEmbeddingBackend(model_name=s.openai_embedding_model)
            raise RuntimeError("Could not initialize an embeddings backend. ") from sentence_error

    raise RuntimeError("Unsupported embedding provider.")
