import hashlib
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..models import Chunk, ChunkMetadata, ParentSection, SourceMeta

_TOKEN_RE = re.compile(r"\S+")
# Sentence boundary: terminator + whitespace + capital/bracket/backtick.
# Avoids splitting "Fig. 1" or "e.g." mid-sentence.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[`])")
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_PY_TOPLEVEL_DEF_RE = re.compile(
    r"^(?P<indent> {0,4})(?:async\s+)?(?P<kind>def|class)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


_MARKDOWN_KINDS = {"website", "paper", "documentation", "markdown"}
_CODE_KINDS = {"code"}
_CONFIG_KINDS = {"config"}


def count_tokens(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


def chunk_id_for(source_id: str, span: tuple[int, int], text: str) -> str:
    """Build a per-chunk id of the form <source_id>::<start>-<end>::<hash10>.
    """
    digest = hashlib.sha1(f"{source_id}:{span[0]}:{span[1]}:{text}".encode()).hexdigest()
    return f"{source_id}::{span[0]}-{span[1]}::{digest[:10]}"


def section_id_for(source_id: str, span: tuple[int, int], heading_path: Sequence[str]) -> str:
    """Build a stable parent-section id of the form <source_id>::section::<hash10>.
    """
    digest = hashlib.sha1(f"{source_id}:{span}:{'|'.join(heading_path)}".encode()).hexdigest()
    return f"{source_id}::section::{digest[:10]}"


@dataclass(frozen=True)
class ChunkingConfig:
    target_tokens: int = 220
    max_tokens: int = 320
    min_tokens: int = 40
    overlap_sentences: int = 1


@dataclass(frozen=True)
class _RawSection:
    """Pre-chunking section: heading path + absolute char span + the raw body text.
    """
    heading_path: tuple[str, ...]
    char_span: tuple[int, int]
    text: str


def split_documents(
    sources: Iterable[tuple[SourceMeta, str]],
    source_to_parameters: dict[str, tuple[str, ...]],
    config: ChunkingConfig | None = None,
) -> tuple[list[Chunk], list[ParentSection]]:
    """Top-level entry point: turn (SourceMeta, raw_text) pairs into aligned (chunks, parents).
    """
    config = config or ChunkingConfig()
    chunks: list[Chunk] = []
    parents: list[ParentSection] = []

    for source, raw_text in sources:
        parameter_ids = source_to_parameters.get(source.id, ())
        sections = _sections_for(source, raw_text)
        for raw_section in sections:
            section_chunks = _chunks_from_section(
                source=source,
                section=raw_section,
                parameter_ids=parameter_ids,
                config=config,
            )

            if not section_chunks:
                continue

            chunks.extend(section_chunks)
            parent_id = section_id_for(source.id, raw_section.char_span, raw_section.heading_path)
            parent_summary = _section_summary(raw_section, source)
            parents.append(
                ParentSection(
                    section_id=parent_id,
                    source_id=source.id,
                    source_kind=source.kind,
                    heading_path=raw_section.heading_path,
                    summary=parent_summary,
                    char_span=raw_section.char_span,
                    child_chunk_ids=tuple(c.metadata.chunk_id for c in section_chunks),
                    parameter_ids=parameter_ids,
                )
            )

            for i, child in enumerate(section_chunks):
                meta = child.metadata
                section_chunks[i] = Chunk(
                    metadata=ChunkMetadata(
                        chunk_id=meta.chunk_id,
                        source_id=meta.source_id,
                        source_kind=meta.source_kind,
                        parent_id=parent_id,
                        heading_path=meta.heading_path,
                        char_span=meta.char_span,
                        token_count=meta.token_count,
                        parameter_ids=meta.parameter_ids,
                        doc_kind=meta.doc_kind,
                    ),
                    text=child.text,
                )
            chunks[-len(section_chunks):] = section_chunks

    return chunks, parents


def _sections_for(source: SourceMeta, text: str) -> list[_RawSection]:
    """Takes a SourceMeta (path, kind, title, ...) and the document’s full string text, and returns a list[_RawSection]
    """
    ext = Path(source.local_path).suffix.lower() if source.local_path else ""
    fallback = [_RawSection((source.title,), (0, len(text)), text)]
    if ext == ".md" or source.kind in _MARKDOWN_KINDS:
        sections = _markdown_sections(text) or fallback
        # Synthesize a title-page biblio section so "Who wrote it?" /
        # "Which journal?" questions outrank README/docs name-repetition.
        if source.kind == "paper":
            biblio = _build_paper_biblio_section(source, text)
            if biblio is not None:
                sections = [biblio, *sections]
        return sections
    if ext == ".py" or source.kind in _CODE_KINDS:
        return _python_sections(text, source.title) or fallback
    if ext == ".xml" or source.kind in _CONFIG_KINDS:
        return _xml_sections(text, source.title) or fallback
    if "##" in text or text.lstrip().startswith("# "):
        return _markdown_sections(text) or fallback
    return fallback


def _build_paper_biblio_section(source: SourceMeta, text: str) -> _RawSection | None:
    """Synthesise a "Title page" section from the paper.
    """
    title_match = re.search(r"^# (.+?)\s*$", text, re.MULTILINE)
    if not title_match:
        return None

    title = title_match.group(1).strip()
    fields: list[tuple[str, str]] = []
    body_end = title_match.end()
    cursor = title_match.end()
    # Walk lines after the title until it hits a non-metadata line.
    remaining = text[cursor:]
    for line in remaining.splitlines(keepends=True):
        stripped = line.strip()
        if not stripped:
            body_end = cursor + len(line)
            cursor += len(line)
            continue
        if stripped.startswith("**") and ":**" in stripped:
            label_end = stripped.index(":**")
            label = stripped[2:label_end].strip()
            value = stripped[label_end + 3 :].strip().lstrip("* ").rstrip(" *")
            if label and value:
                fields.append((label, value))
                body_end = cursor + len(line)
                cursor += len(line)
                continue
        break

    if not fields:
        return None

    body_lines = [f"Title: {title}"]
    body_lines.extend(f"{label}: {value}" for label, value in fields)
    body_lines.extend(_biblio_paraphrases(title, fields))
    body = "\n".join(body_lines)
    return _RawSection(
        heading_path=("Title page",),
        char_span=(title_match.start(), body_end),
        text=body,
    )


def _biblio_paraphrases(title: str, fields: list[tuple[str, str]]) -> list[str]:
    """Generate retrieval-friendly paraphrases.
    Each emitted paraphrase rewrites a known field into a
    sentence with the kind of vocabulary a human question would use.
    """
    field_map = {label.lower(): value for label, value in fields}
    paraphrases: list[str] = []

    acronym, expansion = _split_acronym(title)
    if acronym and expansion:
        paraphrases.append(
            f"Acronym: {acronym} stands for {expansion}. The acronym {acronym} expands to {expansion}."
        )

    if authors := field_map.get("authors"):
        paraphrases.append(f"The paper was written by: {authors}.")
    if affiliation := field_map.get("affiliation"):
        paraphrases.append(f"The authors are affiliated with {affiliation}.")
    if corresponding := field_map.get("corresponding author"):
        paraphrases.append(f"The corresponding author is {corresponding}.")
    if citation := field_map.get("citation"):
        paraphrases.append(f"Published in {citation}.")
        if "doi.org/" in citation:
            doi = citation.split("doi.org/", 1)[1].strip().rstrip(".")
            paraphrases.append(f"DOI: {doi}.")
    if keywords := field_map.get("keywords"):
        paraphrases.append(f"Topic keywords: {keywords}.")

    return paraphrases


def _split_acronym(title: str) -> tuple[str | None, str | None]:
    """Pull an (ACRONYM, expansion) pair out of a colon-separated paper title.
    """
    if ":" not in title:
        return (None, None)
    head, tail = title.split(":", 1)
    head = head.strip()
    tail = tail.strip()
    if not head or not tail or len(head) > 20:
        return (None, None)
    if any(c.isupper() for c in head):
        return (head, tail)
    return (None, None)


def _markdown_sections(text: str) -> list[_RawSection]:
    """Split an markdown document into sections, tracking nested heading paths.
    """
    matches = list(_MD_HEADING_RE.finditer(text))
    if not matches:
        return []

    sections: list[_RawSection] = []
    if matches[0].start() > 0:
        intro = text[: matches[0].start()].strip()
        if intro:
            sections.append(_RawSection(("(prelude)",), (0, matches[0].start()), intro))

    heading_stack: list[str] = []
    levels: list[int] = []

    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        # >= so same-level siblings replace each other (## A then ## B is
        # flat, not nested).
        while levels and levels[-1] >= level:
            heading_stack.pop()
            levels.pop()
        heading_stack.append(title)
        levels.append(level)

        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        if not body.strip():
            continue
        sections.append(
            _RawSection(
                heading_path=tuple(heading_stack),
                char_span=(body_start, body_end),
                text=body,
            )
        )
    return sections


def _xml_sections(text: str, fallback_title: str) -> list[_RawSection]:
    """Split an XML document into one section per top-level child element.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    sections: list[_RawSection] = []
    cursor = 0
    body = text
    for child in list(root):
        tag = (child.tag or "").strip()
        if not tag:
            continue
        marker = f"<{tag}"
        idx = body.find(marker, cursor)
        if idx == -1:
            continue
        end_marker = f"</{tag}>"
        end_idx = body.find(end_marker, idx)
        if end_idx == -1:
            end_idx = body.find("<", idx + len(marker))
            if end_idx == -1:
                end_idx = len(body)
        else:
            end_idx += len(end_marker)
        sections.append(
            _RawSection(
                heading_path=(fallback_title, f"<{tag}>"),
                char_span=(idx, end_idx),
                text=body[idx:end_idx],
            )
        )
        cursor = end_idx
    return sections


def _python_sections(text: str, fallback_title: str) -> list[_RawSection]:
    """Split a Python source file into one section per top-level "def" or "class".
    """
    matches = list(_PY_TOPLEVEL_DEF_RE.finditer(text))
    if not matches:
        return []
    sections: list[_RawSection] = []
    if matches[0].start() > 0:
        head = text[: matches[0].start()]
        if head.strip():
            sections.append(_RawSection((fallback_title, "(module-level)"), (0, matches[0].start()), head))
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        kind = match.group("kind")
        name = match.group("name")
        sections.append(
            _RawSection(
                heading_path=(fallback_title, f"{kind} {name}"),
                char_span=(start, end),
                text=text[start:end],
            )
        )
    return sections


def _chunks_from_section(
    source: SourceMeta,
    section: _RawSection,
    parameter_ids: tuple[str, ...],
    config: ChunkingConfig,
) -> list[Chunk]:
    """Chunk one _RawSection into a list of "Chunk" records.
    """
    body_text = section.text.strip()
    if not body_text:
        return []
    ext = Path(source.local_path).suffix.lower() if source.local_path else ""
    if ext == ".md" or source.kind in _MARKDOWN_KINDS:
        doc_kind = "markdown"
    elif ext == ".py" or source.kind in _CODE_KINDS:
        doc_kind = "code"
    elif ext == ".xml" or source.kind in _CONFIG_KINDS:
        doc_kind = "config"
    else:
        doc_kind = "prose"

    units = _split_units(body_text, doc_kind=doc_kind)
    merged = _merge_units(units, config=config)

    base_offset = section.char_span[0] + (len(section.text) - len(section.text.lstrip()))
    out: list[Chunk] = []
    cursor = 0
    for piece in merged:
        token_count = count_tokens(piece)
        if token_count < config.min_tokens and out:
            prev = out[-1]
            joined = f"{prev.text}\n{piece}".strip()
            new_span = (prev.metadata.char_span[0], base_offset + cursor + len(piece))
            out[-1] = Chunk(
                metadata=ChunkMetadata(
                    chunk_id=chunk_id_for(source.id, new_span, joined),
                    source_id=source.id,
                    source_kind=source.kind,
                    parent_id=None,
                    heading_path=section.heading_path,
                    char_span=new_span,
                    token_count=count_tokens(joined),
                    parameter_ids=parameter_ids,
                    doc_kind=doc_kind,
                ),
                text=joined,
            )
            cursor += len(piece)
            continue
        idx = body_text.find(piece, cursor)
        if idx == -1:
            idx = cursor
        cursor = idx + len(piece)
        span = (base_offset + idx, base_offset + idx + len(piece))
        out.append(
            Chunk(
                metadata=ChunkMetadata(
                    chunk_id=chunk_id_for(source.id, span, piece),
                    source_id=source.id,
                    source_kind=source.kind,
                    parent_id=None,
                    heading_path=section.heading_path,
                    char_span=span,
                    token_count=token_count,
                    parameter_ids=parameter_ids,
                    doc_kind=doc_kind,
                ),
                text=piece,
            )
        )
    return out


def _split_units(text: str, doc_kind: str) -> list[str]:
    """Break text into the smallest units the merger composes from.
    """
    if doc_kind in {"code", "config"}:
        lines = text.splitlines(keepends=True)
        return [line for line in lines if line.strip()] or [text]
    sentences = _SENTENCE_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


def _merge_units(units: list[str], config: ChunkingConfig) -> list[str]:
    """Unit merger producing chunk-sized strings under the configured budget.
    """
    if not units:
        return []
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_tokens = 0
    for unit in units:
        unit_tokens = count_tokens(unit)
        if unit_tokens > config.max_tokens:
            if buffer:
                chunks.append(_join_units(buffer))
                buffer, buffer_tokens = [], 0
            chunks.extend(_window_split(unit, config))
            continue
        if buffer_tokens + unit_tokens > config.max_tokens and buffer:
            chunks.append(_join_units(buffer))
            tail = buffer[-config.overlap_sentences:] if config.overlap_sentences else []
            buffer = list(tail)
            buffer_tokens = sum(count_tokens(t) for t in buffer)
        buffer.append(unit)
        buffer_tokens += unit_tokens
        if buffer_tokens >= config.target_tokens:
            chunks.append(_join_units(buffer))
            tail = buffer[-config.overlap_sentences:] if config.overlap_sentences else []
            buffer = list(tail)
            buffer_tokens = sum(count_tokens(t) for t in buffer)
    if buffer:
        chunks.append(_join_units(buffer))
    return [c for c in chunks if c.strip()]


def _join_units(units: list[str]) -> str:
    """Recompose merged units into a chunk body with the right inter-unit separator.
    """
    if not units:
        return ""
    if all(u.endswith("\n") for u in units):
        return "".join(units).rstrip()
    return " ".join(u.strip() for u in units if u.strip())


def _window_split(text: str, config: ChunkingConfig) -> list[str]:
    """Last-resort splitter for a single oversized unit: sliding token windows.
    """
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return []
    out: list[str] = []
    step = max(1, config.target_tokens - 20)
    for start in range(0, len(tokens), step):
        window = tokens[start:start + config.max_tokens]
        if not window:
            break
        out.append(" ".join(window))
        if start + config.max_tokens >= len(tokens):
            break
    return out


def _section_summary(section: _RawSection, source: SourceMeta) -> str:
    """Build the embedded summary for a parent section (heading path + first meaningful line).
    """
    head = " > ".join(section.heading_path) or source.title
    body = section.text.strip()
    first = _first_meaningful_line(body, max_chars=400)
    return f"{head}\n{first}" if first else head


def _first_meaningful_line(text: str, max_chars: int) -> str:
    """Pick the first informative line of "text" (>= 30 chars), truncated to "max_chars".
    """
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) >= 30:
            return stripped[:max_chars]
    return text.strip()[:max_chars]
