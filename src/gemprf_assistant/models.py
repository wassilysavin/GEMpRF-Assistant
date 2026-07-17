from dataclasses import dataclass, field
from enum import Enum


class AnswerStatus(str, Enum):
    """Truthful outcome of one analyze() pass (str-valued: JSON output stays 'supported' etc.)."""

    SUPPORTED = "supported"                        # grounded LLM answer
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"  # honest refusal
    DEGRADED = "degraded"                          # a fallback produced the text; see fallback kind
    MECHANISM = "mechanism"                        # clarification reframed the matrix as a deliberate answer


class FallbackKind(str, Enum):
    """Which fallback produced the answer text (NONE for a grounded LLM answer or plain refusal)."""

    NONE = "none"
    RELATION = "relation"                  # curated parameter-relation answer
    PARAMETER_MATRIX = "parameter_matrix"  # universal interaction matrix (still 'unanswered' for intake)
    MODEL_CAPABILITY = "model_capability"  # deterministic pRF-model capability answer
    CODE_ENTITY = "code_entity"            # grounded card for a named code module/class/function
    EXTRACTIVE = "extractive"              # LLM unavailable: stitched evidence sentences
    MECHANISM_REFRAME = "mechanism_reframe"  # clarification's final matrix reframe


@dataclass(frozen=True)
class SourceMeta:
    id: str
    title: str
    kind: str
    url: str | None = None
    local_path: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class ParameterSpec:
    id: str
    label: str
    aliases: tuple[str, ...]
    xml_path: str
    summary: str
    significance: str
    impacts: tuple[str, ...]
    source_ids: tuple[str, ...] = ()
    code_source_ids: tuple[str, ...] = ()
    related_parameters: tuple[str, ...] = ()
    enum_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChunkMetadata:
    chunk_id: str
    source_id: str
    source_kind: str
    parent_id: str | None
    heading_path: tuple[str, ...]
    char_span: tuple[int, int]
    token_count: int
    parameter_ids: tuple[str, ...]
    doc_kind: str 


@dataclass(frozen=True)
class ParentSection:
    section_id: str
    source_id: str
    source_kind: str
    heading_path: tuple[str, ...]
    summary: str
    char_span: tuple[int, int]
    child_chunk_ids: tuple[str, ...]
    parameter_ids: tuple[str, ...]


@dataclass(frozen=True)
class Chunk:
    metadata: ChunkMetadata
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float
    rerank_score: float | None = None
    parent_score: float | None = None


@dataclass
class Citation:
    id: str
    title: str
    kind: str
    url: str | None = None
    local_path: str | None = None
    heading_path: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class EvidenceItem:
    source_id: str
    score: float
    text: str
    heading_path: tuple[str, ...] = field(default_factory=tuple)
    parameter_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class AnswerResult:
    answer: str
    status: str
    matched_parameters: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    used_llm: bool = False
    fallback: str = FallbackKind.NONE


@dataclass
class QueryAnalysis:
    question: str
    answer: str
    status: str  # an AnswerStatus value
    matched_parameter_ids: list[str] = field(default_factory=list)
    matched_parameter_labels: list[str] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    used_llm: bool = False
    rerank_used: bool = False
    rewritten_query: str | None = None
    contextualized_question: str | None = None  # follow-up resolved against history (None if unchanged)
    fallback: str = FallbackKind.NONE  # a FallbackKind value
