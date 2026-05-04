import os
from typing import Protocol, Sequence

import numpy as np

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
        """Return one L2-normalised float32 vector per text in 'texts'.
        """
        ...


class SentenceTransformerEmbeddingBackend:

    def __init__(self, model_name: str, local_files_only: bool = False) -> None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed.")
        self.backend_name = f"sentence-transformers:{model_name}"
        self._model = SentenceTransformer(model_name, local_files_only=local_files_only)

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return _normalize_rows(vectors)


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


def build_embedding_backend() -> EmbeddingBackend:
    provider = os.getenv("GEMPRF_ASSISTANT_EMBEDDING_PROVIDER", "").strip().lower()

    if provider == "openai":
        model_name = os.getenv("GEMPRF_ASSISTANT_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        return OpenAIEmbeddingBackend(model_name=model_name)

    if provider == "xai":
        model_name = os.getenv("GEMPRF_ASSISTANT_XAI_EMBEDDING_MODEL", "").strip()
        if not model_name:
            raise RuntimeError(
                "Set 'GEMPRF_ASSISTANT_XAI_EMBEDDING_MODEL' to an embedding model available on your xAI account."
            )
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise RuntimeError("Set `XAI_API_KEY` to use xAI embeddings.")
        return OpenAIEmbeddingBackend(
            model_name=model_name,
            api_key=api_key,
            base_url=os.getenv("GEMPRF_ASSISTANT_XAI_BASE_URL", "https://api.x.ai/v1"),
        )

    if provider in {"openai-compatible", "openai_compatible"}:
        model_name = os.getenv("GEMPRF_ASSISTANT_OPENAI_COMPAT_EMBEDDING_MODEL", "").strip()
        api_key = os.getenv("GEMPRF_ASSISTANT_OPENAI_COMPAT_API_KEY", "").strip()
        base_url = os.getenv("GEMPRF_ASSISTANT_OPENAI_COMPAT_BASE_URL", "").strip()
        if not (model_name and api_key and base_url):
            raise RuntimeError(
                "Set 'GEMPRF_ASSISTANT_OPENAI_COMPAT_EMBEDDING_MODEL', "
                "'GEMPRF_ASSISTANT_OPENAI_COMPAT_API_KEY', and 'GEMPRF_ASSISTANT_OPENAI_COMPAT_BASE_URL'."
            )
        return OpenAIEmbeddingBackend(model_name=model_name, api_key=api_key, base_url=base_url)

    allow_download = os.getenv("GEMPRF_ASSISTANT_EMBEDDING_ALLOW_DOWNLOAD", "").strip().lower() in {"1", "true", "yes"}
    local_only = not allow_download
    sentence_model = os.getenv(
        "GEMPRF_ASSISTANT_EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )

    if provider in {"", "sentence-transformers", "sentence_transformers", "local"}:
        try:
            return SentenceTransformerEmbeddingBackend(
                model_name=sentence_model,
                local_files_only=local_only,
            )
        except Exception as sentence_error:
            if os.getenv("XAI_API_KEY") and os.getenv("GEMPRF_ASSISTANT_XAI_EMBEDDING_MODEL"):
                return OpenAIEmbeddingBackend(
                    model_name=os.getenv("GEMPRF_ASSISTANT_XAI_EMBEDDING_MODEL"),
                    api_key=os.getenv("XAI_API_KEY"),
                    base_url=os.getenv("GEMPRF_ASSISTANT_XAI_BASE_URL", "https://api.x.ai/v1"),
                )
            if os.getenv("OPENAI_API_KEY"):
                model_name = os.getenv("GEMPRF_ASSISTANT_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
                return OpenAIEmbeddingBackend(model_name=model_name)
            raise RuntimeError(
                "Could not initialize an embeddings backend. "
            ) from sentence_error

    raise RuntimeError(
        "Unsupported embedding provider."
    )
