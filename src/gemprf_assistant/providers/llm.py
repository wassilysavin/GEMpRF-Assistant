"""Chat-LLM factory: the single place the ollama/xai/openai provider dispatch lives."""
from ..config import Settings, get_settings

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - optional dependency
    ChatOpenAI = None

XAI_CHAT_DEFAULT = "grok-4.20-reasoning"
XAI_JUDGE_DEFAULT = "grok-4.3"


def _ollama_llm(s: Settings, temperature: float):
    # Reasoning models (qwen3...) think by default, wasting ~20x latency the pipeline
    # discards; reasoning_effort=none disables it via the /v1 endpoint.
    extra = {"reasoning_effort": s.ollama_reasoning_effort} if s.ollama_reasoning_effort else {}
    return ChatOpenAI(
        model=s.ollama_model,
        api_key=s.ollama_api_key,
        base_url=s.ollama_base_url,
        temperature=temperature,
        max_tokens=s.ollama_max_tokens,
        extra_body=extra or None,
    )


def _xai_llm(s: Settings, temperature: float, default_model: str):
    return ChatOpenAI(
        model=s.xai_model or default_model,
        api_key=s.xai_api_key,
        base_url=s.xai_base_url,
        temperature=temperature,
    )


def build_chat_llm(temperature: float = 0.0, settings: Settings | None = None):
    """Chat LLM for the configured provider (explicit GEMPRF_ASSISTANT_LLM_PROVIDER, else inferred from keys, falling back to local ollama), or None."""
    if ChatOpenAI is None:
        return None
    s = settings or get_settings()
    provider = s.resolve_llm_provider()
    if provider == "ollama":
        return _ollama_llm(s, temperature)
    if provider == "xai":
        return _xai_llm(s, temperature, XAI_CHAT_DEFAULT) if s.xai_api_key else None
    if provider == "openai" and s.openai_api_key:
        return ChatOpenAI(model=s.openai_model, temperature=temperature)
    return None


def build_judge_llm(settings: Settings | None = None):
    """Eval-judge LLM: same dispatch as build_chat_llm but with the judge's xAI default model."""
    if ChatOpenAI is None:
        return None
    s = settings or get_settings()
    provider = s.resolve_llm_provider()
    if provider == "ollama":
        return _ollama_llm(s, temperature=0.0)
    if provider == "xai":
        return _xai_llm(s, temperature=0.0, default_model=XAI_JUDGE_DEFAULT) if s.xai_api_key else None
    if provider == "openai" and s.openai_api_key:
        return ChatOpenAI(model=s.openai_model, temperature=0)
    return None
