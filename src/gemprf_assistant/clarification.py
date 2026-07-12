"""Clarification intake: when the engine can't ground an answer, plan question-specific aspects from the failed analysis (falling back to a fixed checklist), ask one question per round over the engine's public analyze(), fold the replies into the query, and answer once."""
import os
import re
from typing import Callable, Optional

from langchain_core.prompts import ChatPromptTemplate

from .models import QueryAnalysis
from .rag.parameter_relations import PARAMETER_MATRIX
from .rag.prompts import INSUFFICIENT_EVIDENCE_MESSAGE

# The engine's relation fallback returns this universal matrix (status "supported") when it can't ground; treat it as ungrounded.
_MATRIX_PREFIX = PARAMETER_MATRIX.split("\n", 1)[0]

_NO_CLARIFICATION = "NO_CLARIFICATION"

# Static fallback checklist (aspect, canned fallback question), used when the planner is disabled or fails; the canned question keeps the step multi-step if the model declines mid-intake.
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
    "You are a GEM-pRF documentation assistant running a short, structured intake before answering a "
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


PLANNER_SYSTEM_PROMPT = (
    "You plan a short clarification intake for a GEM-pRF documentation assistant. The system "
    "could NOT answer the user's question from the allowed GEM-pRF sources. The user is a "
    "researcher who does NOT know GEM-pRF's parameter names or values -- that is what they are "
    "asking about -- so the intake must elicit their SITUATION, which the system will then map to "
    "the right settings. From the question, the failure reason, and the near-miss evidence, list "
    "the 2-4 aspects of the user's situation that, once known, would let the docs answer. "
    "The user's underlying GOAL is asked separately, so do NOT include it: cover the user's TASK, "
    "STIMULUS, BRAIN REGIONS / VISUAL FIELD, DATA SIZE, HARDWARE, or PRIORITIES (accuracy vs "
    "memory vs runtime), most-important first.\n"
    "NEVER ask them to name a "
    "GEM-pRF parameter/setting or to supply a numeric value -- they don't know those. Reply with "
    "one aspect per line as a short descriptive phrase: no numbering, no questions, no "
    "explanations. If the topic is clearly outside GEM-pRF, reply with exactly "
    + _NO_CLARIFICATION + "."
)

PLANNER_HUMAN_PROMPT = (
    "User question: {question}\n"
    "Why it failed: {failure}\n"
    "{corpus}"
    "\nAspects to clarify (one per line):"
)

# Scope gate: an LLM gate on the bare question can't tell an in-scope-but-vague question ("how
# many should I pick?") from an off-topic one -- both look contentless out of context. The
# discriminator is what the engine already retrieved: even the vaguest in-scope question pulls
# some relevant corpus (top score ~0.008-0.7), off-topic ones sit near-zero (~0.0004-0.0037).
# The floor sits in that gap; it is deliberately low so vague-but-real questions still get an
# intake -- refusing a real question is worse for this feature than a rare off-topic intake.
_DEFAULT_MIN_EVIDENCE_SCORE = 0.005

# Overconfident direct answers land on weak evidence: a grounded answer backed by little relevant
# corpus (top score ~0.1) is usually a confident guess on the wrong section, whereas a genuine
# direct answer sits high (~0.9+). Above this floor we trust the direct answer; below it (but above
# the scope floor) we route the question through clarification instead of returning the shaky answer.
_DEFAULT_DIRECT_CONFIDENCE_FLOOR = 0.15

_MAX_PLANNED_ASPECTS = 4

# Deterministic first intake aspect: always establish the user's goal/intent before anything else.
# Injected in code (not left to the planner, which did not reliably lead with it) so anchorless
# questions ("what number is usually best here?") always recover their topic first.
GOAL_ASPECT = (
    "the user's underlying goal -- what they are ultimately trying to achieve, determine, or fix",
    "What are you ultimately trying to achieve or determine here?",
)


# Semantic question gate: retrieval scores can't tell an anchorless question ("what value should
# I choose?", which retrieves many param chunks at high scores) from a real one, so a small LLM
# classifier decides -- VAGUE (anchorless -> clarify), OFFTOPIC (not GEM-pRF -> refuse), ONTOPIC
# (specific & answerable -> trust a grounded answer). Replaces the brittle evidence-score gates.
_CLASSIFY_SYSTEM_PROMPT = (
    "Classify a GEM-pRF user's question into ONE word:\n"
    "VAGUE = a placeholder asking for a value/number/setting/amount with no referent (of WHAT?), "
    "e.g. 'what value should I choose?', 'how many should there be?', 'what number is best here?'.\n"
    "OFFTOPIC = specific but NOT about GEM-pRF / pRF mapping / fMRI, e.g. 'best pizza topping', "
    "'train a CNN on ImageNet'.\n"
    "ONTOPIC = specific AND about GEM-pRF / pRF / fMRI, e.g. 'what does binarization do?', 'how do "
    "I get accurate fits?', 'can I run without a GPU?'.\n"
    "Answer with exactly one word: VAGUE, OFFTOPIC, or ONTOPIC."
)

_CLASSIFY_HUMAN_PROMPT = "Question: {question}\nOne word:"

_QUESTION_KINDS = ("vague", "offtopic", "ontopic")


def _classify_enabled() -> bool:
    return os.getenv("GEMPRF_ASSISTANT_CLARIFY_CLASSIFY", "1").strip() != "0"


def classify_question(llm, question: str) -> str:
    """Classify the question as 'vague' / 'offtopic' / 'ontopic', or '' when the gate is disabled, there is no LLM, or the reply is unparseable (callers then fall back to the deterministic gates)."""
    if llm is None or not _classify_enabled():
        return ""
    try:
        messages = ChatPromptTemplate.from_messages(
            [("system", _CLASSIFY_SYSTEM_PROMPT), ("human", _CLASSIFY_HUMAN_PROMPT)]
        ).format_messages(question=question)
        response = llm.invoke(messages)
    except Exception:
        return ""
    text = str(getattr(response, "content", response)).upper()
    for kind in _QUESTION_KINDS:
        if kind.upper() in text:
            return kind
    return ""


def _top_evidence(analysis: QueryAnalysis) -> float:
    return max((e.score for e in analysis.evidence), default=0.0)


def _min_evidence_score() -> float:
    return float(os.getenv("GEMPRF_ASSISTANT_CLARIFY_MIN_SCORE", str(_DEFAULT_MIN_EVIDENCE_SCORE)))


def _direct_confidence_floor() -> float:
    return float(os.getenv("GEMPRF_ASSISTANT_CLARIFY_DIRECT_FLOOR", str(_DEFAULT_DIRECT_CONFIDENCE_FLOOR)))


def is_in_scope(analysis: QueryAnalysis) -> bool:
    """Evidence-based scope gate: True when the failed analysis retrieved at least one corpus chunk above the relevance floor (off-topic questions retrieve near-zero); deterministic, no LLM call."""
    return _top_evidence(analysis) >= _min_evidence_score()


def is_overconfident_direct(analysis: QueryAnalysis) -> bool:
    """True when analyze() grounded an answer but on weak evidence (likely a confident guess): route it through clarification instead of trusting it."""
    floor = _direct_confidence_floor()
    return floor > 0 and not is_unanswered(analysis) and _top_evidence(analysis) < floor


def _fewshot_enabled() -> bool:
    return os.getenv("GEMPRF_ASSISTANT_CLARIFY_FEWSHOT", "1").strip() != "0"


def _planner_enabled() -> bool:
    return os.getenv("GEMPRF_ASSISTANT_CLARIFY_PLANNER", "1").strip() != "0"


def _failure_mode(analysis: QueryAnalysis) -> str:
    """Human-readable reason the engine refused, so the planner can target its aspects."""
    if (analysis.answer or "").strip().startswith(_MATRIX_PREFIX):
        return ("the question looks like a parameter-relation (what-if) question that the "
                "system could only meet with a generic parameter matrix")
    return "no sufficiently grounded evidence was found for the question as asked"


def _corpus_block(analysis: QueryAnalysis, max_items: int = 3, snippet_chars: int = 200) -> str:
    """Render the near-miss evidence (matched params + top chunk snippets) the planner should steer toward."""
    lines = []
    if analysis.matched_parameter_labels:
        lines.append("Matched parameters: " + ", ".join(analysis.matched_parameter_labels[:8]))
    for item in analysis.evidence[:max_items]:
        heading = " > ".join(item.heading_path) or item.source_id
        snippet = " ".join(item.text.split())[:snippet_chars]
        lines.append(f"- {heading}: {snippet}")
    if not lines:
        return ""
    return ("What the documentation nearly answered with (aspects should steer the user toward "
            "what these sources cover):\n" + "\n".join(lines) + "\n")


def _fallback_question(aspect: str) -> str:
    """Synthesize the canned mid-intake-decline question for a planned aspect."""
    text = aspect.strip().rstrip(".?!")
    if len(text) > 1 and text[1].islower():
        text = text[0].lower() + text[1:]
    return f"Could you tell me more about {text}?"


def _parse_aspects(text: str) -> list[str]:
    """Extract up to _MAX_PLANNED_ASPECTS clean, deduplicated aspect lines from the planner reply."""
    aspects: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = re.sub(r"^[\s\-\*\d\.\)]+", "", line).strip().strip("\"'`")
        if not line or len(line) > 160 or line.casefold() in seen:
            continue
        seen.add(line.casefold())
        aspects.append(line)
        if len(aspects) >= _MAX_PLANNED_ASPECTS:
            break
    return aspects


def plan_intake_aspects(
    llm, question: str, analysis: QueryAnalysis
) -> Optional[list[tuple[str, str]]]:
    """One LLM call planning question-specific (aspect, canned fallback) pairs from the failed analysis; [] = out-of-scope (refuse without asking), None = planner unavailable/failed (use the static checklist)."""
    if llm is None:
        return None
    try:
        messages = ChatPromptTemplate.from_messages(
            [("system", PLANNER_SYSTEM_PROMPT), ("human", PLANNER_HUMAN_PROMPT)]
        ).format_messages(
            question=question, failure=_failure_mode(analysis), corpus=_corpus_block(analysis)
        )
        response = llm.invoke(messages)
    except Exception:
        return None
    text = str(getattr(response, "content", response)).strip()
    if _NO_CLARIFICATION in text.upper():
        return []
    aspects = _parse_aspects(text)
    if not aspects:
        return None
    return [(aspect, _fallback_question(aspect)) for aspect in aspects]


# Reformulation: the raw folded query ("How many should I pick? mainly foveal, one GPU") does not
# retrieve well; a concrete GEM-pRF query synthesized from the gathered context does. This is the
# "map the user's situation to the right settings" step.
REFORMULATE_SYSTEM_PROMPT = (
    "You turn a vague GEM-pRF user question plus the context gathered from them into ONE concrete, "
    "specific query for GEM-pRF documentation. Translate their plain-language situation into "
    "GEM-pRF terminology (pRF sizes / sigmas, search grid resolution and extent, drift regressors, "
    "measured-data batches, GPU memory, refine fitting, etc.) and name the concept they are really "
    "asking about. Output ONLY the single reformulated question, nothing else."
)

REFORMULATE_HUMAN_PROMPT = (
    "Original question: {question}\n{context}\nConcrete GEM-pRF documentation query:"
)


def _context_block(asked: list[tuple[str, str]]) -> str:
    if not asked:
        return "No extra context was gathered.\n"
    rows = "\n".join(f"- Q: {q}\n  A: {a}" for q, a in asked)
    return f"Context gathered from the user:\n{rows}\n"


def _reformulate_enabled() -> bool:
    return os.getenv("GEMPRF_ASSISTANT_CLARIFY_REFORMULATE", "1").strip() != "0"


def reformulate_query(llm, question: str, asked: list[tuple[str, str]]) -> Optional[str]:
    """Synthesize the vague question + gathered context into one concrete GEM-pRF query (None on error/empty)."""
    if llm is None:
        return None
    try:
        messages = ChatPromptTemplate.from_messages(
            [("system", REFORMULATE_SYSTEM_PROMPT), ("human", REFORMULATE_HUMAN_PROMPT)]
        ).format_messages(question=question, context=_context_block(asked))
        response = llm.invoke(messages)
    except Exception:
        return None
    text = str(getattr(response, "content", response)).strip().strip("\"'`")
    return text or None


# Drift guard: a reformulated query can ground in the WRONG corpus region (e.g. a "how many pRF
# sizes?" query drifting to batching), yielding a confidently-wrong answer -- worse than an honest
# hedge. Verify the grounded answer actually addresses the original question before returning it.
RELEVANCE_SYSTEM_PROMPT = (
    "You check whether a candidate answer actually addresses the user's ORIGINAL question about "
    "GEM-pRF. Consider only topical relevance, not completeness. Answer with exactly one word: "
    "RELEVANT or OFFTOPIC."
)

RELEVANCE_HUMAN_PROMPT = (
    "Original question: {question}\n{context}\nCandidate answer:\n{answer}\n\n"
    "Does the candidate answer address what the user was asking about? One word "
    "(RELEVANT or OFFTOPIC):"
)


def answer_is_relevant(llm, question: str, asked: list[tuple[str, str]], answer: str) -> bool:
    """True unless the model clearly says OFFTOPIC; defaults True on error so the guard never suppresses a good answer."""
    if llm is None:
        return True
    try:
        messages = ChatPromptTemplate.from_messages(
            [("system", RELEVANCE_SYSTEM_PROMPT), ("human", RELEVANCE_HUMAN_PROMPT)]
        ).format_messages(question=question, context=_context_block(asked), answer=answer[:1500])
        response = llm.invoke(messages)
    except Exception:
        return True
    return "OFFTOPIC" not in str(getattr(response, "content", response)).upper().replace(" ", "")


# Mechanism fallback: when even a concrete query can't ground a specific value (the corpus has no
# prescribed number), present the doc-grounded relations as a real answer instead of a refusal.
_MECHANISM_LEAD = (
    "GEM-pRF's documentation doesn't prescribe a single value for your case, but here is how the "
    "relevant settings relate, given what you described:"
)

# The matrix constant carries its own "I can't ground..." refusal preamble; drop it so the
# mechanism answer doesn't double-hedge, keeping only the relations body.
_MATRIX_BODY = PARAMETER_MATRIX.split("\n\n", 1)[1] if "\n\n" in PARAMETER_MATRIX else PARAMETER_MATRIX


def _mechanism_enabled() -> bool:
    return os.getenv("GEMPRF_ASSISTANT_CLARIFY_MECHANISM", "1").strip() != "0"


def _to_mechanism_answer(analysis: QueryAnalysis) -> QueryAnalysis:
    """Reframe the refusal-prefixed matrix fallback as a helpful mechanism answer (in place, returned)."""
    answer = (analysis.answer or "").strip()
    if not answer.startswith(_MATRIX_PREFIX):
        return analysis  # only reframe the matrix body; leave plain refusals untouched
    analysis.answer = f"{_MECHANISM_LEAD}\n\n{_MATRIX_BODY}"
    analysis.status = "mechanism"  # not "insufficient_evidence": this is a deliberate answer
    return analysis


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
    history=None,
) -> QueryAnalysis:
    """Answer a question; if ungrounded, plan question-specific aspects (static checklist as fallback) and walk them (one question/round, folding replies), re-analyzing after each reply and stopping as soon as it grounds (out-of-scope refuses without asking). `history` resolves follow-up references across REPL turns."""
    if max_rounds is None:
        max_rounds = _default_max_rounds()
    analysis = engine.analyze(question, history=history)
    llm = getattr(engine, "llm", None)
    # Judge follow-ups by what they resolve to, not their raw text (a bare "Why" reads as vague).
    standalone = getattr(analysis, "contextualized_question", None) or question
    kind = classify_question(llm, standalone)  # 'vague' | 'offtopic' | 'ontopic' | '' (gate disabled)

    if kind == "offtopic":
        return analysis  # not GEM-pRF: refuse without interrogating

    if not is_unanswered(analysis):
        # Trust a grounded direct answer only for a specific question. A VAGUE (anchorless) answer
        # is a scattershot guess, so clarify. With the classifier off, fall back to the evidence
        # floor (a confident answer on weak evidence is also an overconfident guess).
        if kind == "ontopic":
            return analysis
        if not kind and not is_overconfident_direct(analysis):
            return analysis

    if llm is None:
        return analysis

    if _planner_enabled():
        if not kind and not is_in_scope(analysis):
            return analysis  # deterministic scope fallback when the classifier didn't run
        planned = plan_intake_aspects(llm, standalone, analysis)
        if planned == []:
            return analysis  # planner's own gate agreed it's out of scope
        # Always lead with the goal question, then the planner's situation aspects.
        aspects = [GOAL_ASPECT] + (planned or [])
    else:
        aspects = INTAKE_ASPECTS

    target = min(len(aspects), max_rounds)
    asked: list[tuple[str, str]] = []
    replies: list[str] = []
    for i in range(target):
        aspect, fallback = aspects[i]
        clarifying = generate_intake_question(llm, standalone, aspect, asked)
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
        # Cheap early exit: if the raw fold happens to ground already, take it.
        analysis = engine.analyze(" ".join([standalone, *replies]), history=history)
        if not is_unanswered(analysis):
            return analysis

    if not asked:
        return analysis  # nothing gathered (immediate EOF/quit) -> answer with what we have

    # Map the gathered situation to a concrete GEM-pRF query and re-analyze: this is what actually
    # grounds the answerable questions that the raw fold never could.
    if _reformulate_enabled():
        concrete = reformulate_query(llm, standalone, asked)
        if concrete:
            reanalyzed = engine.analyze(concrete, history=history)
            if not is_unanswered(reanalyzed):
                # Only return it if it actually addresses the original question; a drifted answer
                # (grounded in the wrong corpus region) falls through to the honest mechanism answer.
                if answer_is_relevant(llm, standalone, asked, reanalyzed.answer):
                    return reanalyzed
            else:
                analysis = reanalyzed  # carry the concrete-query evidence into the mechanism fallback

    # Still no specific answer: present the doc-grounded relations as a real mechanism answer
    # (conditioned on the gathered context) rather than a bare refusal.
    if _mechanism_enabled():
        return _to_mechanism_answer(analysis)
    return analysis
