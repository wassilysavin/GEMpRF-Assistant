"""Query-expansion stage: HyDE / keyword rewrite behind the rare-anchor gate, plus follow-up detection."""
import re

from langchain_core.prompts import ChatPromptTemplate

from .. import tracing
from ..config import get_settings
from ..models import ParameterSpec
from ..observability import get_logger
from .prompts import HYDE_SYSTEM_PROMPT, QUERY_REWRITE_SYSTEM_PROMPT

logger = get_logger(__name__)

_SUBJECT_PATTERNS = (
    re.compile(r"^\s*what\s+does\s+(.+?)\s+(?:stand\s+for|mean|denote|describe|do)\b", re.IGNORECASE),
    re.compile(r"^\s*what\s+is\s+meant\s+by\s+['\"]?(.+?)['\"]?(?:\s+in\b|\s+for\b|$)", re.IGNORECASE),
    re.compile(r"^\s*what\s+(?:kind|type|sort)\s+of\s+(.+?)(?:\s+(?:is|are|do|does)\b|$)", re.IGNORECASE),
    re.compile(r"^\s*what\s+(?:is|are)\s+(.+?)(?:\s+(?:in|for|of|on|at)\b|$)", re.IGNORECASE),
    re.compile(r"^\s*(?:define|explain|describe)\s+(.+?)(?:\s+(?:in|for|of|on|at)\b|$)", re.IGNORECASE),
)

# Tokens specific enough that bare retrieval beats LLM query expansion.
_RARE_ANCHOR_PATTERNS = (
    re.compile(r"\([^)]+\)"),                                # parenthesised: C(θ)
    re.compile(r"[θΘα-ωΑ-Ω∇∑∫]"),                            # Greek / math
    re.compile(r"\b[A-Za-z]{2,}-[A-Za-z]{2,}\b"),            # hyphenated: GEM-pRF
    re.compile(r"\b\w*[a-z][A-Z]\w*\b"),                     # mixed-case: pRF
    re.compile(r"\b\w+_\w+\b"),                              # snake_case identifier: measured_data
    re.compile(r"\b[A-Za-z_]\w*\.\w+"),                      # dotted attribute/path: cfg.measured_data
    re.compile(r"\[\s*['\"]"),                               # subscript access: cfg[...]["batches"]
)


def is_followup_rewrite(original: str, contextual: str) -> bool:
    """True when the condense step meaningfully rewrote the question (a real follow-up), ignoring case/punctuation/whitespace-only reformatting."""
    def norm(s: str) -> str:
        return " ".join((s or "").lower().split()).strip(" ?.!")
    return norm(contextual) != norm(original)


def extract_subject(question: str) -> str | None:
    """Pull out the noun phrase a definitional question is about (the X in "what is X")."""
    q = question.strip().rstrip("?.!")
    for pattern in _SUBJECT_PATTERNS:
        m = pattern.match(q)
        if m:
            return m.group(1).strip(" '\"")
    return None


def subject_has_rare_anchor(subject: str, parameters: dict[str, ParameterSpec]) -> bool:
    """True if 'subject' carries a token specific enough that LLM query expansion would dilute retrieval."""
    for pattern in _RARE_ANCHOR_PATTERNS:
        if pattern.search(subject):
            return True
    s_lower = subject.lower()
    for spec in parameters.values():
        for name in (spec.id, spec.label, *spec.aliases):
            if not name or len(name) < 3:
                continue
            if re.search(rf"\b{re.escape(name.lower())}\b", s_lower):
                return True
    return False


def expansion_skip_reason(llm, question: str, parameters: dict[str, ParameterSpec]) -> str:
    """Why expand_query passed the question through unchanged (for the trace span)."""
    settings = get_settings()
    if not settings.hyde and not settings.query_rewrite:
        return "expansion disabled (GEMPRF_ASSISTANT_HYDE=0, GEMPRF_ASSISTANT_QUERY_REWRITE=0)"
    if llm is None:
        return "no LLM configured"
    subject = extract_subject(question) or question
    if subject_has_rare_anchor(subject, parameters):
        return f"rare-anchor gate: subject '{subject}' already retrieves well bare"
    return "LLM expansion returned nothing usable"


def hyde_query(llm, question: str, parameters: dict[str, ParameterSpec]) -> str | None:
    """HyDE expansion: append a hypothetical answer passage to the retrieval query (gated off by default)."""
    if not get_settings().hyde or llm is None:
        return None
    subject = extract_subject(question) or question
    if subject_has_rare_anchor(subject, parameters):
        return None
    try:
        prompt = ChatPromptTemplate.from_messages([("system", HYDE_SYSTEM_PROMPT), ("human", "{question}")])
        response = (prompt | llm).invoke({"question": question}, **tracing.invoke_kwargs())
        hypothetical = str(response.content).strip()
    except Exception as exc:
        logger.warning("HyDE expansion failed, retrieving on the bare question: %s", exc)
        return None
    hypothetical = hypothetical.strip("\"'`")
    # < 20 chars -> almost certainly a refusal/empty completion.
    if len(hypothetical) < 20:
        return None
    return f"{question.strip()} {hypothetical}"


def rewrite_query(llm, question: str, parameters: dict[str, ParameterSpec]) -> str | None:
    """Append LLM-suggested domain keywords to the original question for retrieval only."""
    if not get_settings().query_rewrite or llm is None:
        return None
    # Rare-anchor gate: a code identifier already retrieves well, so skip expansion that dilutes it.
    subject = extract_subject(question) or question
    if subject_has_rare_anchor(subject, parameters):
        return None
    try:
        prompt = ChatPromptTemplate.from_messages(
            [("system", QUERY_REWRITE_SYSTEM_PROMPT), ("human", "{question}")]
        )
        response = (prompt | llm).invoke({"question": question}, **tracing.invoke_kwargs())
        keywords_raw = str(response.content).strip()
    except Exception as exc:
        logger.warning("query rewrite failed, retrieving on the bare question: %s", exc)
        return None
    keywords_raw = keywords_raw.strip("\"'`")
    parts = re.split(r"[,\n]", keywords_raw)
    keywords: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        kw = raw.strip().lstrip("-•*").strip().strip("\"'`")
        if not kw or len(kw) > 80 or kw.endswith("?"):
            continue
        lower = kw.lower()
        if lower in seen or lower in question.lower():
            continue
        seen.add(lower)
        keywords.append(kw)
    if not keywords:
        return None
    return f"{question.strip()} {' '.join(keywords)}"
