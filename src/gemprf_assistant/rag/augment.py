"""Synthetic-question augmentation: prepend generated questions to each chunk's
embedded text (cached; stored text unchanged) so paraphrased queries match. Gated by GEMPRF_ASSISTANT_HYPO_QUESTIONS=1."""
import hashlib
import json
import os
from pathlib import Path

_CACHE_PATH = Path(os.getenv(
    "GEMPRF_ASSISTANT_HYPO_CACHE",
    str(Path(__file__).resolve().parents[3] / "data" / "hypo_questions.json"),
))
_N = int(os.getenv("GEMPRF_ASSISTANT_HYPO_N", "4"))

_PROMPT = (
    "You write search questions that the given passage directly answers. "
    "Output exactly {n} short, varied questions a real user might type — use "
    "synonyms and different phrasings, not the passage's exact wording. One per "
    "line, no numbering, no preamble."
)


def hypo_questions_enabled() -> bool:
    return os.getenv("GEMPRF_ASSISTANT_HYPO_QUESTIONS", "0").strip() == "1"


def _key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=0))


def _build_llm():
    """A small local model is plenty for question generation (it is not answer
    quality). Defaults to ollama qwen2.5:7b; honors the usual provider envs."""
    from langchain_openai import ChatOpenAI
    if os.getenv("XAI_API_KEY") and os.getenv("GEMPRF_ASSISTANT_HYPO_PROVIDER", "ollama") == "xai":
        return ChatOpenAI(model=os.getenv("GEMPRF_ASSISTANT_XAI_MODEL", "grok-4.3"),
                          api_key=os.getenv("XAI_API_KEY"),
                          base_url=os.getenv("GEMPRF_ASSISTANT_XAI_BASE_URL", "https://api.x.ai/v1"),
                          temperature=0.4, max_tokens=256)
    return ChatOpenAI(model=os.getenv("GEMPRF_ASSISTANT_HYPO_MODEL", "qwen2.5:7b"),
                      api_key="ollama", base_url="http://localhost:11434/v1",
                      temperature=0.4, max_tokens=256)


def augment_texts(texts: list[str], *, llm=None, progress=None) -> list[str]:
    """Return, per input chunk text, '<q1>\\n<q2>...\\n\\n<chunk text>' when enabled,
    else the original text unchanged. Cached by chunk hash."""
    if not hypo_questions_enabled():
        return list(texts)
    import re
    cache = _load_cache()
    llm = llm or _build_llm()
    sys_prompt = _PROMPT.format(n=_N)
    from langchain_core.prompts import ChatPromptTemplate
    chain = ChatPromptTemplate.from_messages(
        [("system", sys_prompt), ("human", "Passage:\n{c}\n\nQuestions:")]) | llm

    out, dirty = [], False
    for i, text in enumerate(texts):
        k = _key(text)
        qs = cache.get(k)
        if qs is None:
            try:
                raw = str(chain.invoke({"c": text[:1500]}).content)
                qs = [re.sub(r"^[\s\-\d\.\)]+", "", l).strip() for l in raw.splitlines() if l.strip()]
                qs = [q for q in qs if len(q) > 8][:_N]
            except Exception:
                qs = []
            cache[k] = qs; dirty = True
        out.append(("\n".join(qs) + "\n\n" + text) if qs else text)
        if progress:
            progress(i + 1, len(texts))
    if dirty:
        _save_cache(cache)
    return out
