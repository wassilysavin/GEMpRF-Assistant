"""Pack and install prebuilt index snapshots (weaviate/ + kg.ttl) so installed users can skip ingestion."""
import json
import shutil
import tarfile
import tempfile
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from ..paths import data_dir

MANIFEST_NAME = "snapshot_manifest.json"


def _backend_name() -> str:
    """Best-effort name of the currently configured embedding backend (the one that built the index)."""
    try:
        from ..providers import build_embedding_backend
        return build_embedding_backend().backend_name
    except Exception:
        return "unknown"


def pack(out: str | None = None) -> Path:
    """Archive the current index plus a manifest into a .tar.gz; returns the archive path."""
    root = data_dir()
    if not (root / "weaviate").is_dir():
        raise SystemExit(f"No index at {root / 'weaviate'}; run scripts/ingest.py first.")
    try:
        pkg_version = version("GEMpRF-Assistant")
    except PackageNotFoundError:
        pkg_version = "unknown"
    contents = ["weaviate"] + (["kg.ttl"] if (root / "kg.ttl").exists() else [])
    manifest = {
        "format": 1,
        "package_version": pkg_version,
        "embedding_backend": _backend_name(),
        "contents": contents,
    }
    dest = Path(out).expanduser() if out else Path.cwd() / "gemprf-index-snapshot.tar.gz"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest, "w:gz") as tar:
        for name in contents:
            tar.add(root / name, arcname=name)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
            json.dump(manifest, tmp, indent=2)
        tar.add(tmp.name, arcname=MANIFEST_NAME)
        Path(tmp.name).unlink()
    return dest


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    try:
        tar.extractall(dest, filter="data")
    except TypeError:
        # Python without the filter arg: reject members escaping dest, then extract.
        for member in tar.getmembers():
            if not (dest / member.name).resolve().is_relative_to(dest.resolve()):
                raise SystemExit(f"Unsafe path in archive: {member.name}")
        tar.extractall(dest)


def install(source: str, force: bool = False) -> dict:
    """Fetch a snapshot (local path or http(s) URL) and extract it into the data dir; returns its manifest."""
    root = data_dir()
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "snapshot.tar.gz"
        if source.startswith(("http://", "https://")):
            urllib.request.urlretrieve(source, archive)
        else:
            shutil.copy(Path(source).expanduser(), archive)
        staged = Path(td) / "extracted"
        with tarfile.open(archive, "r:gz") as tar:
            _safe_extract(tar, staged)
        manifest_path = staged / MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        items = [p for p in staged.iterdir() if p.name != MANIFEST_NAME]
        clashes = [str(root / p.name) for p in items if (root / p.name).exists()]
        if clashes and not force:
            raise SystemExit("Already present (pass --force to replace): " + ", ".join(clashes))
        root.mkdir(parents=True, exist_ok=True)
        for item in items:
            target = root / item.name
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            shutil.move(str(item), target)
    return manifest
