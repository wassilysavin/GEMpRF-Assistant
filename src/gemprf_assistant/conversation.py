"""In-session conversation history: a rolling window of answered turns so follow-up questions can resolve references ("it", "that parameter", "what value in my case?") by an LLM condense step rather than hand-written phrase patterns."""
import os
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate

_DEFAULT_MAX_TURNS = 4
# Per-turn answer cap keeps the history block's LLM prefill bounded.
_ANSWER_CHAR_CAP = 500

# Condense a follow-up into a standalone question using the conversation. The model decides
# whether the question depends on prior turns -- no phrase list to maintain or outgrow.
_CONDENSE_SYSTEM = (
    "You rewrite a user's latest question into a STANDALONE GEM-pRF question. If it refers to "
    "something from the conversation ('it', 'that parameter', 'what value in my case?'), fold that "
    "referent in so the question stands on its own. If it is already self-contained, return it "
    "UNCHANGED. Do not answer it, do not add new topics -- output only the rewritten question."
)

_CONDENSE_HUMAN = "Conversation:\n{history}\n\nLatest question: {question}\n\nStandalone question:"


def history_enabled() -> bool:
    """Conversation history toggle (env GEMPRF_ASSISTANT_HISTORY, default on)."""
    return os.getenv("GEMPRF_ASSISTANT_HISTORY", "1").strip() != "0"


def _max_turns() -> int:
    """Rolling-window size (env GEMPRF_ASSISTANT_HISTORY_TURNS, default 4)."""
    try:
        return max(1, int(os.getenv("GEMPRF_ASSISTANT_HISTORY_TURNS", str(_DEFAULT_MAX_TURNS))))
    except ValueError:
        return _DEFAULT_MAX_TURNS


@dataclass(frozen=True)
class ConversationTurn:
    question: str
    answer: str


class ConversationHistory:
    """Keeps the last N answered turns of one session (REPL); engines stay stateless."""

    def __init__(self, max_turns: int | None = None) -> None:
        self.max_turns = max_turns if max_turns is not None else _max_turns()
        self.turns: list[ConversationTurn] = []

    def __bool__(self) -> bool:
        return bool(self.turns)

    def add(self, question: str, answer: str) -> None:
        """Record one answered turn, trimming the answer to the per-turn cap."""
        answer = " ".join((answer or "").split())
        if len(answer) > _ANSWER_CHAR_CAP:
            answer = answer[:_ANSWER_CHAR_CAP].rsplit(" ", 1)[0] + " …"
        self.turns.append(ConversationTurn(question.strip(), answer))
        if len(self.turns) > self.max_turns:
            del self.turns[: len(self.turns) - self.max_turns]

    def render(self) -> str:
        """Render turns as a User/Assistant block for the answer prompt ('- none' when empty)."""
        if not self.turns:
            return "- none"
        return "\n".join(f"User: {t.question}\nAssistant: {t.answer}" for t in self.turns)

    def contextualize(self, question: str, llm=None) -> str:
        """Rewrite a follow-up into a standalone question via the LLM (returns it unchanged with no history, no llm, or on error)."""
        if not self.turns or llm is None:
            return question
        try:
            messages = ChatPromptTemplate.from_messages(
                [("system", _CONDENSE_SYSTEM), ("human", _CONDENSE_HUMAN)]
            ).format_messages(history=self.render(), question=question)
            response = llm.invoke(messages)
        except Exception:
            return question
        text = str(getattr(response, "content", response)).strip().strip("\"'`")
        return text or question
