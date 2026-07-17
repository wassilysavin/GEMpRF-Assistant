"""Corpus loading: curated sources, grounding documents, and parameter specs from kb/corpus/ data files,
plus auto-discovery of the external/ submodule trees. Validation happens at load time via pydantic."""
from functools import lru_cache
from pathlib import Path

import yaml
from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict

from ..models import ParameterSpec, SourceMeta
from ..paths import corpus_root

ROOT = corpus_root()
_CORPUS_DIR = Path(__file__).parent / "corpus"


def _path(relative_path: str) -> str:
    return str((ROOT / relative_path).resolve())


class _SourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    kind: str
    url: str | None = None
    local_path: str | None = None
    description: str | None = None


class _ParameterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    aliases: list[str]
    xml_path: str
    summary: str
    significance: str
    impacts: list[str]
    source_ids: list[str] = []
    code_source_ids: list[str] = []
    related_parameters: list[str] = []
    enum_values: list[str] = []


@lru_cache(maxsize=1)
def _load_curated_sources() -> tuple[SourceMeta, ...]:
    raw = yaml.safe_load((_CORPUS_DIR / "sources.yaml").read_text(encoding="utf-8"))
    sources = []
    for entry in raw:
        m = _SourceModel.model_validate(entry)
        sources.append(SourceMeta(
            id=m.id, title=m.title, kind=m.kind, url=m.url,
            local_path=_path(m.local_path) if m.local_path else None,
            description=m.description,
        ))
    return tuple(sources)


@lru_cache(maxsize=1)
def _load_parameters() -> tuple[ParameterSpec, ...]:
    raw = yaml.safe_load((_CORPUS_DIR / "parameters.yaml").read_text(encoding="utf-8"))
    source_ids = {s.id for s in _load_curated_sources()}
    parameters = []
    for entry in raw:
        m = _ParameterModel.model_validate(entry)
        unknown = (set(m.source_ids) | set(m.code_source_ids)) - source_ids
        if unknown:
            raise ValueError(f"parameter {m.id} references unknown sources: {sorted(unknown)}")
        parameters.append(ParameterSpec(
            id=m.id, label=m.label, aliases=tuple(m.aliases), xml_path=m.xml_path,
            summary=m.summary, significance=m.significance, impacts=tuple(m.impacts),
            source_ids=tuple(m.source_ids), code_source_ids=tuple(m.code_source_ids),
            related_parameters=tuple(m.related_parameters), enum_values=tuple(m.enum_values),
        ))
    return tuple(parameters)


@lru_cache(maxsize=1)
def _load_grounding_documents() -> tuple[Document, ...]:
    """One markdown file per grounding document: YAML frontmatter (source), byte-exact body."""
    source_ids = {s.id for s in _load_curated_sources()}
    documents = []
    for path in sorted((_CORPUS_DIR / "grounding").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError(f"{path.name}: missing frontmatter")
        header, _, body = text[4:].partition("\n---\n")
        meta = yaml.safe_load(header)
        sid = meta.get("source")
        if sid not in source_ids:
            raise ValueError(f"{path.name}: unknown source '{sid}'")
        documents.append(Document(page_content=body.removesuffix("\n"), metadata={"source_id": sid}))
    return tuple(documents)


def __getattr__(name: str):
    """Lazy module attributes so importing the loader never reads the corpus files eagerly."""
    if name == "CURATED_SOURCES":
        return _load_curated_sources()
    if name == "PARAMETERS":
        return _load_parameters()
    if name == "MANUAL_DOCUMENTS":
        return _load_grounding_documents()
    if name == "ALL_SOURCES":
        return _all_sources()
    raise AttributeError(name)


@lru_cache(maxsize=1)
def _all_sources() -> tuple[SourceMeta, ...]:
    return _load_curated_sources() + _discover_supplementary_sources()


_GITHUB_REPO_ROOT = Path(_path("external/github/GEMpRF"))
_DEMOKIT_ROOT = Path(_path("external/GEMpRF-DemoKit"))
_WHEEL_RELATIVE_MARKER = "gemprf_wheel/"

_INDEXABLE_EXTS: tuple[tuple[str, str], ...] = (
    (".py", "code"),
    (".md", "markdown"),
    (".xml", "config"),
)

_SKIP_RELATIVE_DIRS: tuple[tuple[str, ...], ...] = (
    ("example_data",),
    ("tests", "temp"),
    ("tests", "testdata"),
)


def _curated_wheel_relative_paths() -> set[str]:
    relatives: set[str] = set()
    for source in _load_curated_sources():
        if not source.local_path:
            continue
        posix = Path(source.local_path).as_posix()
        marker_index = posix.find(_WHEEL_RELATIVE_MARKER)
        if marker_index == -1:
            continue
        relatives.add(posix[marker_index + len(_WHEEL_RELATIVE_MARKER):])
    return relatives


def _curated_local_paths() -> set[Path]:
    return {Path(s.local_path).resolve() for s in _load_curated_sources() if s.local_path}


def _is_skipped(path: Path, root: Path) -> bool:
    if path.name == "__init__.py":
        return True
    rel_parts = path.relative_to(root).parts
    for skip in _SKIP_RELATIVE_DIRS:
        if len(rel_parts) >= len(skip) and tuple(rel_parts[: len(skip)]) == skip:
            return True
        for i in range(len(rel_parts) - len(skip) + 1):
            if tuple(rel_parts[i : i + len(skip)]) == skip:
                return True
    return False


def _discover_tree(
    root: Path,
    id_prefix: str,
    title_prefix: str,
    skip_wheel_relpaths: set[str] | None = None,
) -> list[SourceMeta]:
    if not root.is_dir():
        return []

    discovered: list[SourceMeta] = []
    curated = _curated_local_paths()

    for ext, kind in _INDEXABLE_EXTS:
        for path in sorted(root.rglob(f"*{ext}")):
            if _is_skipped(path, root):
                continue
            resolved = path.resolve()
            if resolved in curated:
                continue
            relative = resolved.relative_to(root)
            if skip_wheel_relpaths and relative.as_posix() in skip_wheel_relpaths:
                continue
            dotted = ".".join(relative.with_suffix("").parts).replace(" ", "_")
            discovered.append(
                SourceMeta(
                    id=f"{id_prefix}.{dotted}",
                    title=f"{title_prefix}: {relative.as_posix()}",
                    kind=kind,
                    local_path=str(resolved),
                    description=(
                        f"Auto-indexed {ext.lstrip('.')} from {title_prefix} "
                        f"({relative.as_posix()})."
                    ),
                )
            )
    return discovered


def _discover_supplementary_sources() -> tuple[SourceMeta, ...]:
    discovered: list[SourceMeta] = []
    discovered.extend(
        _discover_tree(
            _GITHUB_REPO_ROOT,
            id_prefix="github",
            title_prefix="gemprf/GEMpRF",
            skip_wheel_relpaths=_curated_wheel_relative_paths(),
        )
    )
    discovered.extend(
        _discover_tree(
            _DEMOKIT_ROOT,
            id_prefix="demokit",
            title_prefix="GEMpRF-DemoKit",
        )
    )
    return tuple(discovered)


def source_map() -> dict[str, SourceMeta]:
    return {source.id: source for source in _all_sources()}


def parameter_map() -> dict[str, ParameterSpec]:
    return {parameter.id: parameter for parameter in _load_parameters()}


def ensure_local_sources_exist() -> None:
    missing = []
    for source in _all_sources():
        if source.local_path and not Path(source.local_path).exists():
            missing.append(source.local_path)
    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(
            "Missing required local GEM-pRF sources:\n"
            f"{joined}"
        )


def _load_local_document(source: SourceMeta) -> Document:
    path = Path(source.local_path or "")
    text = path.read_text(encoding="utf-8")
    header = f"{source.title}\nSource type: {source.kind}\nLocal path: {path}\n"
    if source.description:
        header += f"Description: {source.description}\n"
    return Document(page_content=f"{header}\n{text}", metadata={"source_id": source.id})


def load_documents() -> list[Document]:
    ensure_local_sources_exist()
    documents = list(_load_grounding_documents())
    for source in _all_sources():
        if source.local_path:
            documents.append(_load_local_document(source))
    return documents
