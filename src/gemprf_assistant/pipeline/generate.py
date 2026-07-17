"""Generation stage: grounded LLM answer with retries, refusal normalization, and extractive degradation."""
import re
import time

from langchain_core.prompts import ChatPromptTemplate

from .. import tracing
from ..config import get_settings
from ..models import FallbackKind, ParameterSpec, RetrievedChunk
from ..observability import get_logger
from .assemble import evidence_context, parameter_context, strip_citations
from .prompts import HUMAN_PROMPT, INSUFFICIENT_EVIDENCE_MESSAGE, SYSTEM_PROMPT

logger = get_logger(__name__)


def generate_answer(
    llm,
    question: str,
    matched_specs: list[ParameterSpec],
    evidence: list[RetrievedChunk],
    rewritten_query: str | None = None,
    history=None,
) -> tuple[str, bool, FallbackKind]:
    """Return (answer, used_llm, fallback): LLM answer, honest refusal, or extractive degradation."""
    if llm is not None:
        attempts = get_settings().llm_retries
        last_exc = None
        for i in range(attempts):
            try:
                answer = _generate_with_llm(llm, question, matched_specs, evidence, rewritten_query, history)
                # Match the refusal sentinel anywhere: small models wrap it in a preamble ("...Therefore: INSUFFICIENT_EVIDENCE:..."), which startswith misses and then surfaces as a bogus grounded answer.
                if "INSUFFICIENT_EVIDENCE" not in answer.upper():
                    return strip_citations(answer), True, FallbackKind.NONE
                return INSUFFICIENT_EVIDENCE_MESSAGE, False, FallbackKind.NONE
            except Exception as exc:  # usually transient (rate limit / timeout)
                last_exc = exc
                if i < attempts - 1:
                    time.sleep(1.5 * (i + 1))
        # Degrade to extractive only after retries; log it so silent fallbacks stay
        # visible instead of looking like real answers.
        logger.warning(
            "LLM failed after %d attempts (%s: %.160s); degrading to extractive answer",
            attempts, type(last_exc).__name__, str(last_exc),
        )
    extracted = extractive(evidence)
    if extracted == INSUFFICIENT_EVIDENCE_MESSAGE:
        return extracted, False, FallbackKind.NONE
    return extracted, False, FallbackKind.EXTRACTIVE


def _generate_with_llm(
    llm,
    question: str,
    matched_specs: list[ParameterSpec],
    evidence: list[RetrievedChunk],
    rewritten_query: str | None = None,
    history=None,
) -> str:
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)])
    response = (prompt | llm).invoke({
        "question": question,
        "history_context": history.render() if history else "- none",
        "expanded_query_context": rewritten_query or "- none",
        "parameter_context": parameter_context(matched_specs),
        "evidence_context": evidence_context(evidence),
    }, **tracing.invoke_kwargs())
    return str(response.content).strip()


def extractive(evidence: list[RetrievedChunk]) -> str:
    """LLM-free fallback: stitch up to 3 sentences from the top-3 chunks plus a disclaimer."""
    if not evidence:
        return INSUFFICIENT_EVIDENCE_MESSAGE
    sentences: list[str] = []
    seen: set[str] = set()
    for r in evidence[:3]:
        for sentence in re.split(r"(?<=[.!?])\s+", r.chunk.text):
            stripped = sentence.strip()
            if len(stripped) < 30 or stripped in seen:
                continue
            sentences.append(stripped)
            seen.add(stripped)
            if len(sentences) >= 3:
                break
        if len(sentences) >= 3:
            break
    if not sentences:
        return INSUFFICIENT_EVIDENCE_MESSAGE
    sentences.append("This summary is constrained to the allowed GEM-pRF sources.")
    return " ".join(sentences)
