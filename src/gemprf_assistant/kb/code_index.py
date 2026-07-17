"""Static extraction of GEM-pRF code entities and their relations, grounded to file:line.

Produces the corpus/code_entities.json artifact that the refusal-path fallback serves when a
question literally names a module, class, or function. Every field is read from the source AST,
so nothing here is asserted beyond what the code states; regenerating keeps it from drifting."""
import ast
import json
from pathlib import Path

from . import loader

ARTIFACT_PATH = Path(__file__).parent / "corpus" / "code_entities.json"
_ARTIFACT_VERSION = 1
_MAX_CALLS = 16  # keep each card's relation lists readable
_REPO_GEM_ROOT = loader._GITHUB_REPO_ROOT / "gem"


def _repo_sibling(local_path: str) -> str | None:
    """Repo copy of a file addressed by its gem-relative path; used when a wheel copy won't parse."""
    parts = Path(local_path).parts
    if "gem" not in parts:
        return None
    candidate = _REPO_GEM_ROOT.joinpath(*parts[parts.index("gem") + 1:])
    resolved = str(candidate)
    return resolved if candidate.is_file() and resolved != str(Path(local_path)) else None


def _module_dotted(local_path: str) -> str:
    """Dotted module name rooted at the tool package (gem.*), consistent across wheel and repo copies."""
    parts = Path(local_path).with_suffix("").parts
    if "gem" in parts:
        parts = parts[parts.index("gem"):]
    return ".".join(parts)


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Render a parameter list from the AST (names + markers + '=' for present defaults; no annotations)."""
    a = node.args
    out: list[str] = []
    pos = [*a.posonlyargs, *a.args]
    n_defaults = len(a.defaults)
    first_default = len(pos) - n_defaults
    for i, arg in enumerate(pos):
        out.append(f"{arg.arg}=..." if i >= first_default else arg.arg)
        if a.posonlyargs and i == len(a.posonlyargs) - 1:
            out.append("/")
    if a.vararg:
        out.append(f"*{a.vararg.arg}")
    elif a.kwonlyargs:
        out.append("*")
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        out.append(f"{arg.arg}=..." if default is not None else arg.arg)
    if a.kwarg:
        out.append(f"**{a.kwarg.arg}")
    return f"({', '.join(out)})"


def _doc(node) -> str:
    """First non-empty line of the entity's own docstring, or an empty string."""
    text = ast.get_docstring(node) or ""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _called_names(node) -> list[str]:
    """Distinctive names invoked inside a function body (Name or Attribute callees), order-preserving."""
    seen: dict[str, None] = {}
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            if name and not name.startswith("_") and len(name) >= 4:
                seen.setdefault(name, None)
    return list(seen)[:_MAX_CALLS]


def _imported_names(tree: ast.Module) -> list[str]:
    """Top-level imports of the module (module names and from-imported symbols), order-preserving."""
    seen: dict[str, None] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                seen.setdefault(alias.name.split(".")[0], None)
        elif isinstance(node, ast.ImportFrom) and node.module:
            seen.setdefault(node.module, None)
    return list(seen)


def _base_names(node: ast.ClassDef) -> list[str]:
    """Base-class names as written (Name or dotted Attribute), skipping unparseable bases."""
    names: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def _entities_for_source(source_id: str, local_path: str) -> list[dict]:
    """Extract module + class + function/method entities (with relations) from one source file.

    A truncated/unparseable curated copy (e.g. a broken wheel file) recovers from its repo sibling,
    which holds the same code at the same gem-relative path; the original source_id is kept for citation."""
    try:
        tree = ast.parse(Path(local_path).read_text(encoding="utf-8"))
    except SyntaxError:
        sibling = _repo_sibling(local_path)
        if sibling is None:
            raise
        tree = ast.parse(Path(sibling).read_text(encoding="utf-8"))
        local_path = sibling
    module = _module_dotted(local_path)
    file_rel = loader._relative_to_corpus(Path(local_path))

    def base(kind: str, name: str, qualname: str, line: int) -> dict:
        return {
            "id": f"{source_id}::{qualname}", "kind": kind, "name": name, "qualname": qualname,
            "source_id": source_id, "module": module, "file": file_rel, "line": line,
        }

    entities: list[dict] = []
    top_classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    top_funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    mod = base("module", module.rsplit(".", 1)[-1], module, 1)
    mod["doc"] = _doc(tree)
    mod["contains"] = [c.name for c in top_classes] + [f.name for f in top_funcs]
    mod["imports"] = _imported_names(tree)
    entities.append(mod)

    for cls in top_classes:
        methods = [m for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
        ent = base("class", cls.name, cls.name, cls.lineno)
        ent["doc"] = _doc(cls)
        ent["bases"] = _base_names(cls)
        ent["contains"] = [m.name for m in methods]
        entities.append(ent)
        for m in methods:
            me = base("method", m.name, f"{cls.name}.{m.name}", m.lineno)
            me["doc"] = _doc(m)
            me["signature"] = _signature(m)
            me["calls"] = _called_names(m)
            entities.append(me)

    for func in top_funcs:
        fe = base("function", func.name, func.name, func.lineno)
        fe["doc"] = _doc(func)
        fe["signature"] = _signature(func)
        fe["calls"] = _called_names(func)
        entities.append(fe)

    return entities


def build_code_entities() -> dict:
    """Extract every code entity from the registered code-kind sources (main-path index)."""
    entities: list[dict] = []
    skipped: list[str] = []
    for source in sorted(loader._all_sources(), key=lambda s: s.id):
        if source.kind != "code" or not source.local_path:
            continue
        try:
            entities.extend(_entities_for_source(source.id, source.local_path))
        except SyntaxError:
            skipped.append(source.id)
    return {"version": _ARTIFACT_VERSION, "entities": entities, "skipped": skipped}


def write_artifact(path: Path = ARTIFACT_PATH) -> dict:
    """Regenerate corpus/code_entities.json and return summary counts."""
    data = build_code_entities()
    path.write_text(json.dumps(data, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    kinds: dict[str, int] = {}
    for e in data["entities"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return {"entities": len(data["entities"]), "by_kind": kinds, "skipped": data["skipped"]}
