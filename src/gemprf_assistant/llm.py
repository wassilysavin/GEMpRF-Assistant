"""Shared chat-LLM factory: the single place the ollama/xai/openai provider dispatch lives."""
import os

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - optional dependency
    ChatOpenAI = None


def build_chat_llm(temperature: float = 0.0):
    """Return a chat LLM for the configured provider (GEMPRF_ASSISTANT_LLM_PROVIDER, else inferred from keys, falling back to local ollama), or None."""
    if ChatOpenAI is None:
        return None
    provider = os.getenv("GEMPRF_ASSISTANT_LLM_PROVIDER", "").strip().lower()
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_xai = bool(os.getenv("XAI_API_KEY"))

    if provider == "ollama" or (not provider and not has_openai and not has_xai):
        return ChatOpenAI(
            model=os.getenv("GEMPRF_ASSISTANT_OLLAMA_MODEL", "mistral-nemo:12b"),
            api_key=os.getenv("GEMPRF_ASSISTANT_OLLAMA_API_KEY", "ollama"),
            base_url=os.getenv("GEMPRF_ASSISTANT_OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            temperature=temperature,
            max_tokens=int(os.getenv("GEMPRF_ASSISTANT_OLLAMA_MAX_TOKENS", "768")),
        )
    if provider == "xai" or (not provider and has_xai and not has_openai):
        if not has_xai:
            return None
        return ChatOpenAI(
            model=os.getenv("GEMPRF_ASSISTANT_XAI_MODEL", "grok-4.20-reasoning"),
            api_key=os.getenv("XAI_API_KEY"),
            base_url=os.getenv("GEMPRF_ASSISTANT_XAI_BASE_URL", "https://api.x.ai/v1"),
            temperature=temperature,
        )
    if not has_openai:
        return None
    return ChatOpenAI(model=os.getenv("GEMPRF_ASSISTANT_MODEL", "gpt-4o-mini"), temperature=temperature)
