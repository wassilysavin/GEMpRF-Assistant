"""Central typed settings: every GEMPRF_ASSISTANT_* env var is declared, parsed, and defaulted here.

Precedence is env var > user config file (`gemprf-assistant config set`) > default.
Call get_settings() at use time (it re-reads both, so tests can monkeypatch);
long-lived components may hold onto one Settings instance for a consistent view.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .paths import (  # noqa: F401  (re-exported: config is the one import site for paths)
    corpus_root,
    data_dir,
    user_config_path,
)

_PREFIX = "GEMPRF_ASSISTANT_"

# Keys accepted in the user config file: the ones a first-run user legitimately pins.
# Everything else stays env-only (tuning knobs, not user choices).
USER_CONFIG_KEYS = ("llm_provider", "ollama_model", "xai_model", "model", "embedding_model")


def _user_config() -> dict[str, str]:
    """The persisted user choices; unreadable or malformed files are ignored (env/defaults still work)."""
    try:
        data = json.loads(user_config_path().read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: str(v) for k, v in data.items() if k in USER_CONFIG_KEYS and v is not None}


def _lookup(name: str) -> str | None:
    """Env var, else the user config file, else None."""
    value = os.getenv(_PREFIX + name)
    if value is not None:
        return value
    return _user_config().get(name.lower())


def _str(name: str, default: str = "") -> str:
    value = _lookup(name)
    return default if value is None else value


def _opt(name: str) -> str | None:
    value = _lookup(name)
    return value if value else None


def _flag_on(name: str) -> bool:
    """Default-on toggle: anything but 0/false/no/off keeps it enabled."""
    return _str(name, "1").strip().lower() not in {"0", "false", "no", "off"}


def _flag_off(name: str) -> bool:
    """Default-off toggle: only an explicit 1/true/yes enables it."""
    return _str(name, "").strip().lower() in {"1", "true", "yes"}


def _int(name: str, default: int, floor: int | None = None) -> int:
    try:
        value = int(_str(name, str(default)))
    except ValueError:
        return default
    return max(floor, value) if floor is not None else value


def _float(name: str, default: float) -> float:
    try:
        return float(_str(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # LLM provider ("" = infer from keys, else ollama/xai/openai)
    llm_provider: str
    openai_api_key: str | None
    xai_api_key: str | None
    ollama_model: str
    ollama_api_key: str
    ollama_base_url: str
    ollama_max_tokens: int
    ollama_reasoning_effort: str
    xai_model: str | None  # per-consumer defaults live in providers.llm
    xai_base_url: str
    openai_model: str
    llm_retries: int
    evidence_char_cap: int

    # Retrieval / rerank
    hybrid_alpha: float
    rerank_pool: int
    reranker_enabled: bool
    reranker_model: str | None
    reranker_allow_download: bool
    reranker_device: str | None
    code_recall: bool
    hyde: bool
    query_rewrite: bool
    relations_enabled: bool

    # Embeddings
    embedding_provider: str
    embedding_model: str
    embedding_allow_download: bool
    embed_query_prefix: str | None
    embed_doc_prefix: str | None
    openai_embedding_model: str
    xai_embedding_model: str | None
    openai_compat_embedding_model: str
    openai_compat_api_key: str
    openai_compat_base_url: str

    # Weaviate
    weaviate_mode: str
    weaviate_path: str | None
    weaviate_host: str
    weaviate_http_port: int
    weaviate_grpc_port: int
    weaviate_embedded_http_port: int
    weaviate_embedded_grpc_port: int

    # Conversation / clarification
    history_enabled: bool
    history_turns: int
    clarify_classify: bool
    clarify_fewshot: bool
    clarify_planner: bool
    clarify_reformulate: bool
    clarify_mechanism: bool
    clarify_min_score: float
    clarify_direct_floor: float
    clarify_max_rounds: int | None  # None = one round per intake aspect

    # Misc
    preflight_enabled: bool
    kg_path: str | None
    log_level: str

    def resolve_llm_provider(self) -> str | None:
        """The shared ollama/xai/openai dispatch rule (explicit provider, else inferred from keys)."""
        provider = self.llm_provider.strip().lower()
        if provider:
            return provider if provider in {"ollama", "xai", "openai"} else None
        if not self.openai_api_key and not self.xai_api_key:
            return "ollama"
        if self.xai_api_key and not self.openai_api_key:
            return "xai"
        return "openai" if self.openai_api_key else None

    def resolved_weaviate_path(self) -> str:
        return self.weaviate_path or str(data_dir() / "weaviate")

    def corpus_root_path(self) -> Path:
        return corpus_root()

    def resolved_kg_path(self) -> Path:
        return Path(self.kg_path) if self.kg_path else data_dir() / "kg.ttl"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_provider=_str("LLM_PROVIDER"),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            xai_api_key=os.getenv("XAI_API_KEY") or None,
            ollama_model=_str("OLLAMA_MODEL", "mistral-nemo:12b"),
            ollama_api_key=_str("OLLAMA_API_KEY", "ollama"),
            ollama_base_url=_str("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            ollama_max_tokens=_int("OLLAMA_MAX_TOKENS", 768),
            ollama_reasoning_effort=_str("OLLAMA_REASONING_EFFORT", "").strip(),
            xai_model=_opt("XAI_MODEL"),
            xai_base_url=_str("XAI_BASE_URL", "https://api.x.ai/v1"),
            openai_model=_str("MODEL", "gpt-4o-mini"),
            llm_retries=_int("LLM_RETRIES", 3),
            evidence_char_cap=_int("LLM_EVIDENCE_CHAR_CAP", 0, floor=0),
            hybrid_alpha=_float("HYBRID_ALPHA", 0.5),
            rerank_pool=_int("RERANK_POOL", 12, floor=1),
            reranker_enabled=_flag_on("RERANKER_ENABLED"),
            reranker_model=_opt("RERANKER_MODEL"),
            reranker_allow_download=_flag_off("RERANKER_ALLOW_DOWNLOAD"),
            reranker_device=_opt("RERANKER_DEVICE"),
            code_recall=_flag_on("CODE_RECALL"),
            hyde=_str("HYDE", "0").strip() == "1",
            query_rewrite=_flag_on("QUERY_REWRITE"),
            relations_enabled=_flag_on("RELATIONS"),
            embedding_provider=_str("EMBEDDING_PROVIDER").strip().lower(),
            embedding_model=_str("EMBEDDING_MODEL", "intfloat/e5-large-v2"),
            embedding_allow_download=_flag_off("EMBEDDING_ALLOW_DOWNLOAD"),
            embed_query_prefix=os.getenv(_PREFIX + "EMBED_QUERY_PREFIX"),
            embed_doc_prefix=os.getenv(_PREFIX + "EMBED_DOC_PREFIX"),
            openai_embedding_model=_str("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
            xai_embedding_model=_opt("XAI_EMBEDDING_MODEL"),
            openai_compat_embedding_model=_str("OPENAI_COMPAT_EMBEDDING_MODEL", "").strip(),
            openai_compat_api_key=_str("OPENAI_COMPAT_API_KEY", "").strip(),
            openai_compat_base_url=_str("OPENAI_COMPAT_BASE_URL", "").strip(),
            weaviate_mode=_str("WEAVIATE_MODE", "embedded").strip().lower(),
            weaviate_path=_opt("WEAVIATE_PATH"),
            weaviate_host=_str("WEAVIATE_HOST", "localhost"),
            weaviate_http_port=_int("WEAVIATE_HTTP_PORT", 8080),
            weaviate_grpc_port=_int("WEAVIATE_GRPC_PORT", 50051),
            weaviate_embedded_http_port=_int("WEAVIATE_EMBEDDED_HTTP_PORT", 8079),
            weaviate_embedded_grpc_port=_int("WEAVIATE_EMBEDDED_GRPC_PORT", 50050),
            history_enabled=_str("HISTORY", "1").strip() != "0",
            history_turns=_int("HISTORY_TURNS", 4, floor=1),
            clarify_classify=_str("CLARIFY_CLASSIFY", "1").strip() != "0",
            clarify_fewshot=_str("CLARIFY_FEWSHOT", "1").strip() != "0",
            clarify_planner=_str("CLARIFY_PLANNER", "1").strip() != "0",
            clarify_reformulate=_str("CLARIFY_REFORMULATE", "1").strip() != "0",
            clarify_mechanism=_str("CLARIFY_MECHANISM", "1").strip() != "0",
            clarify_min_score=_float("CLARIFY_MIN_SCORE", 0.005),
            clarify_direct_floor=_float("CLARIFY_DIRECT_FLOOR", 0.15),
            clarify_max_rounds=(lambda raw: max(1, int(raw)) if raw else None)(_str("CLARIFY_MAX_ROUNDS", "")),
            preflight_enabled=_str("PREFLIGHT", "1").strip().lower() not in {"0", "false", "no"},
            kg_path=_opt("KG_PATH"),
            log_level=_str("LOG_LEVEL", "WARNING").strip().upper(),
        )


def get_settings() -> Settings:
    """Fresh Settings from the current environment (cheap; safe under test monkeypatching)."""
    return Settings.from_env()
