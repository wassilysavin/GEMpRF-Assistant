"""Context-assembly stage: evidence selection, curated-code injection, citations, prompt slots."""
import re

from ..config import get_settings
from ..models import Citation, EvidenceItem, ParameterSpec, RetrievedChunk, SourceMeta

_MIN_EVIDENCE_SCORE = 1e-6
_MAX_CITATIONS = 6

# Curated code-source recall: guarantee a confidently-matched parameter's own code reaches the LLM,
# independent of how the (HyDE/prose) retrieval query happens to rank code chunks for a phrasing.
_CODE_RECALL_MIN_SCORE = 0.6   # param-match confidence gate (mirrors the fallback gate)
_CODE_RECALL_POOL = 6          # candidate code chunks fetched from the curated sources
_CODE_RECALL_MAX = 2           # max code chunks appended as reserved evidence slots
_CODE_STUB_MAX_TOKENS = 24     # skip trivial stubs (class line, bare __init__) so the logic body wins

# Strips bracketed source-id citations like [paper.full] from LLM answers before they reach the user.
_CITATION_BRACKET_RE = re.compile(r"\s*\[[a-z]+(?:\.[a-z0-9_-]+)+(?:\s[^\]]+)?\]")


def strip_citations(text: str) -> str:
    """Remove residual '[source.id]' citations from an LLM answer and tidy the whitespace."""
    cleaned = _CITATION_BRACKET_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned.strip()


def _cap_text(text: str, cap: int) -> str:
    """Truncate text to `cap` chars on a word boundary (cap<=0 or short text -> unchanged)."""
    if cap <= 0 or len(text) <= cap:
        return text
    return text[:cap].rsplit(" ", 1)[0] + " …"


def select_evidence(candidates: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    return candidates[:top_k]


def has_supporting_evidence(evidence: list[RetrievedChunk], rerank_used: bool) -> bool:
    if not evidence:
        return False
    return max(r.score for r in evidence) >= _MIN_EVIDENCE_SCORE


def inject_code_evidence(
    evidence: list[RetrievedChunk],
    matched_specs: list[ParameterSpec],
    matched_scores: dict[str, float],
    query: str,
    *,
    sources: dict[str, SourceMeta],
    embedding_backend,
    vector_store,
    alpha: float,
) -> list[RetrievedChunk]:
    """Append the top matched parameter's curated code chunk(s) if not already present.

    Fires only when the parameter clears the confidence gate (guards off-topic). Appends
    rather than reorders, so prose-led top_k — and conceptual answers — stay unchanged; the
    code is merely made available for the answer prompt to quote when the question wants it.
    """
    if not get_settings().code_recall or not matched_specs:
        return evidence
    top = matched_specs[0]
    if matched_scores.get(top.id, 0.0) < _CODE_RECALL_MIN_SCORE:
        return evidence
    source_ids = tuple(sid for sid in top.code_source_ids if sid in sources)
    if not source_ids:
        return evidence
    _embed_q = getattr(embedding_backend, "embed_query", embedding_backend.embed_texts)
    hits = vector_store.chunks_by_source_ids(
        query=query,
        vector=_embed_q([query])[0],
        limit=_CODE_RECALL_POOL,
        alpha=alpha,
        source_ids=source_ids,
    )
    present = {r.chunk.metadata.chunk_id for r in evidence}
    injected = 0
    for hit in hits:
        if injected >= _CODE_RECALL_MAX:
            break
        meta = hit.chunk.metadata
        if meta.chunk_id in present or meta.token_count <= _CODE_STUB_MAX_TOKENS:
            continue
        evidence.append(RetrievedChunk(chunk=hit.chunk, score=float(hit.score)))
        present.add(meta.chunk_id)
        injected += 1
    return evidence


def to_evidence_items(evidence: list[RetrievedChunk]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            source_id=r.chunk.metadata.source_id,
            score=float(r.rerank_score) if r.rerank_score is not None else float(r.score),
            text=r.chunk.text,
            heading_path=r.chunk.metadata.heading_path,
            parameter_ids=r.chunk.metadata.parameter_ids,
        )
        for r in evidence
    ]


def build_citations(
    evidence: list[RetrievedChunk],
    matched_specs: list[ParameterSpec],
    sources: dict[str, SourceMeta],
) -> list[Citation]:
    """Build the citation list from retrieved chunks plus matched parameters."""
    seen: set[tuple[str, tuple[str, ...]]] = set()
    citations: list[Citation] = []
    for r in evidence:
        sid = r.chunk.metadata.source_id
        heading = r.chunk.metadata.heading_path
        key = (sid, heading)
        if key in seen or sid not in sources:
            continue
        source = sources[sid]
        citations.append(
            Citation(
                id=source.id,
                title=source.title,
                kind=source.kind,
                url=source.url,
                local_path=source.local_path,
                heading_path=heading,
            )
        )
        seen.add(key)
        if len(citations) >= _MAX_CITATIONS:
            return citations

    for parameter in matched_specs:
        for sid in (*parameter.source_ids, *parameter.code_source_ids):
            if sid not in sources:
                continue
            key = (sid, ())
            if key in seen:
                continue
            source = sources[sid]
            citations.append(
                Citation(
                    id=source.id,
                    title=source.title,
                    kind=source.kind,
                    url=source.url,
                    local_path=source.local_path,
                )
            )
            seen.add(key)
            if len(citations) >= _MAX_CITATIONS:
                return citations
    return citations


def parameter_context(matched_specs: list[ParameterSpec]) -> str:
    """Render matched parameters as a bullet list for the human prompt."""
    if not matched_specs:
        return "- none"
    return "\n".join(
        f"- {p.label} ({p.xml_path}): {p.summary} {p.significance}"
        for p in matched_specs
    )


def evidence_context(evidence: list[RetrievedChunk]) -> str:
    """Render retrieved evidence as [source_id heading_path] text blocks."""
    if not evidence:
        return "- none"
    cap = get_settings().evidence_char_cap
    return "\n\n".join(
        f"[{r.chunk.metadata.source_id} {' > '.join(r.chunk.metadata.heading_path)}] {_cap_text(r.chunk.text, cap)}"
        for r in evidence
    )


def chunk_summaries(chunks: list[RetrievedChunk]) -> list[dict]:
    """Compact per-chunk view (ids, heading, scores, preview) for trace spans."""
    return [
        {
            "chunk_id": r.chunk.metadata.chunk_id,
            "source_id": r.chunk.metadata.source_id,
            "heading": " > ".join(r.chunk.metadata.heading_path),
            "score": float(r.score),
            "rerank_score": float(r.rerank_score) if r.rerank_score is not None else None,
            "preview": r.chunk.text[:200],
        }
        for r in chunks
    ]
