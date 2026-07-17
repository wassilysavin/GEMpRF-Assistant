from dataclasses import dataclass, field


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


@dataclass
class QueryAnalysis:
    question: str
    answer: str
    status: str
    matched_parameter_ids: list[str] = field(default_factory=list)
    matched_parameter_labels: list[str] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    used_llm: bool = False
    rerank_used: bool = False
    rewritten_query: str | None = None
    contextualized_question: str | None = None  # follow-up resolved against history (None if unchanged)
