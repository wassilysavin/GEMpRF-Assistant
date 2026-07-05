"""Clarification intake: when the engine can't ground an answer, ask the user a fixed checklist of questions (over the engine's public analyze(), no internals touched), fold the replies into the query, and answer once."""
import os
from typing import Callable, Optional

from langchain_core.prompts import ChatPromptTemplate

from .models import QueryAnalysis
from .rag.parameter_relations import PARAMETER_MATRIX
from .rag.prompts import INSUFFICIENT_EVIDENCE_MESSAGE

# The engine's relation fallback returns this universal matrix (status "supported") when it can't ground; treat it as ungrounded.
_MATRIX_PREFIX = PARAMETER_MATRIX.split("\n", 1)[0]

_NO_CLARIFICATION = "NO_CLARIFICATION"

# Fixed checklist (aspect, canned fallback question); the fallback keeps the step multi-step if the model declines mid-intake.
INTAKE_ASPECTS = (
    ("the goal and scope: which visual areas or ROI, and what the user is trying to map or achieve",
     "What are you trying to map or achieve, and in which visual areas or ROI?"),
    ("the main priority or trade-off: accuracy vs GPU memory vs runtime",
     "What matters most here -- accuracy, GPU memory, or runtime?"),
    ("which specific GEM-pRF parameter, setting, or analysis stage the question is really about",
     "Which specific GEM-pRF parameter or setting are you asking about?"),
    ("any hard constraints: GPU memory size, dataset size, or time budget",
     "Do you have any hard constraints, such as GPU memory, dataset size, or a time budget?"),
)

INTAKE_SYSTEM_PROMPT = (
    "You are a GEM-pRF documentation assistant running a short, fixed intake before answering a "
    "question the system could NOT answer directly from the allowed GEM-pRF sources. You will be "
    "told which ONE aspect to ask about this turn. Ask a single short question about ONLY that "
    "aspect. Do NOT ask the user for the current numeric value of their own config, do NOT answer "
    "the question yourself, do NOT ask more than one thing, and never repeat or reword a question "
    "already asked below. If the whole topic is clearly outside GEM-pRF's documentation, reply with "
    "exactly " + _NO_CLARIFICATION + ". Reply with only the question (or " + _NO_CLARIFICATION + ")."
)

INTAKE_HUMAN_PROMPT = (
    "User question: {question}\n"
    "Ask about THIS aspect only: {aspect}\n"
    "{prior}"
    "\nYour single question:"
)

# Few-shot exemplars steer small local models toward scope/goal questions; toggle with GEMPRF_ASSISTANT_CLARIFY_FEWSHOT=0.
CLARIFY_FEWSHOT = (
    "\n\nExamples of the STYLE to use (ask about scope/goal/trade-off, never the user's current "
    "numeric setting):\n"
    "GOOD: Which visual areas are you mapping, and is your priority staying within GPU memory or "
    "keeping fine spatial resolution?\n"
    "BAD: What is your current num_horizontal_prfs?\n"
    "GOOD: Are the small receptive fields mainly foveal, or spread across the visual field?\n"
    "BAD: What are your current sigma values?"
)


def _fewshot_enabled() -> bool:
    return os.getenv("GEMPRF_ASSISTANT_CLARIFY_FEWSHOT", "1").strip() != "0"


def is_unanswered(analysis: QueryAnalysis) -> bool:
    """True when analyze() didn't ground an answer: the refusal, the status-lies refusal, or the engine's parameter-matrix fallback."""
    answer = (analysis.answer or "").strip()
    return (
        analysis.status == "insufficient_evidence"
        or answer == INSUFFICIENT_EVIDENCE_MESSAGE
        or answer.startswith(_MATRIX_PREFIX)
    )


def _prior_block(asked: list[tuple[str, str]]) -> str:
    """Render the questions already asked and how the user answered them."""
    if not asked:
        return ""
    rows = "\n".join(f"- Asked: {q}\n  User answered: {a}" for q, a in asked)
    return f"Already asked this session (do NOT repeat or reword these):\n{rows}\n"


def generate_intake_question(
    llm, question: str, aspect: str, asked: Optional[list[tuple[str, str]]] = None
) -> Optional[str]:
    """Ask the LLM for one intake question about `aspect` (None if it declines with NO_CLARIFICATION or errors); `asked` is the history so it doesn't repeat."""
    if llm is None:
        return None
    system_prompt = INTAKE_SYSTEM_PROMPT + (CLARIFY_FEWSHOT if _fewshot_enabled() else "")
    try:
        messages = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", INTAKE_HUMAN_PROMPT)]
        ).format_messages(question=question, aspect=aspect, prior=_prior_block(asked or []))
        response = llm.invoke(messages)
    except Exception:
        return None
    text = str(getattr(response, "content", response)).strip().strip("\"'`")
    if not text or _NO_CLARIFICATION in text.upper():
        return None
    return text


def _default_max_rounds() -> int:
    return max(1, int(os.getenv("GEMPRF_ASSISTANT_CLARIFY_MAX_ROUNDS", str(len(INTAKE_ASPECTS)))))


def answer_with_clarification(
    engine,
    question: str,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    max_rounds: Optional[int] = None,
) -> QueryAnalysis:
    """Answer a question; if ungrounded, walk the aspect checklist (one question/round, folding replies), re-analyzing after each reply and stopping as soon as it grounds (out-of-scope refuses without asking)."""
    if max_rounds is None:
        max_rounds = _default_max_rounds()
    analysis = engine.analyze(question)
    if not is_unanswered(analysis):
        return analysis

    llm = getattr(engine, "llm", None)
    if llm is None:
        return analysis

    target = min(len(INTAKE_ASPECTS), max_rounds)
    asked: list[tuple[str, str]] = []
    replies: list[str] = []
    for i in range(target):
        aspect, fallback = INTAKE_ASPECTS[i]
        clarifying = generate_intake_question(llm, question, aspect, asked)
        if clarifying is None:
            if i == 0:
                return analysis  # out-of-scope gate: decline on the first aspect -> refuse
            clarifying = fallback  # in-scope: keep the intake multi-step with a canned question
        output_fn(f"\nI need a bit more to answer that. {clarifying}")
        try:
            reply = input_fn("your answer> ").strip()
        except EOFError:
            break  # no reply available (piped/closed stdin) -> answer with what we have
        if not reply or reply.lower() in {"quit", "exit", "cancel", "stop"}:
            break
        asked.append((clarifying, reply))
        replies.append(reply)
        # Re-ground after each reply and stop early once the folded context is answerable,
        # rather than always exhausting the aspect checklist.
        analysis = engine.analyze(" ".join([question, *replies]))
        if not is_unanswered(analysis):
            return analysis

    return analysis
