"""Index manifest: records what built the index so an embedder/corpus mismatch fails fast
instead of silently searching a stale or dimensionally-incompatible index."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from ..observability import get_logger
from ..paths import data_dir

MANIFEST_NAME = "index_manifest.json"
SCHEMA_VERSION = 1
# Bump when chunking changes chunk boundaries or ids (forces a rebuild prompt).
CHUNKING_VERSION = 1

logger = get_logger(__name__)


def manifest_path() -> Path:
    return data_dir() / MANIFEST_NAME


def corpus_sha(documents) -> str:
    """Hash of exactly what gets chunked+embedded (source ids + page contents, in order)."""
    h = hashlib.sha256()
    for d in documents:
        h.update(d.metadata["source_id"].encode())
        h.update(b"\0")
        h.update(d.page_content.encode())
        h.update(b"\0")
    return h.hexdigest()


def write_manifest(
    *, embedder: str, embedding_dim: int, corpus_hash: str,
    doc_count: int, chunk_count: int, section_count: int,
) -> dict:
    data = {
        "schema_version": SCHEMA_VERSION,
        "chunking_version": CHUNKING_VERSION,
        "embedder": embedder,
        "embedding_dim": embedding_dim,
        "corpus_sha256": corpus_hash,
        "doc_count": doc_count,
        "chunk_count": chunk_count,
        "section_count": section_count,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    return data


def load_manifest() -> dict | None:
    try:
        return json.loads(manifest_path().read_text())
    except (OSError, json.JSONDecodeError):
        return None


def verify_compatible(embedder: str) -> None:
    """Fail fast when the configured embedder differs from the one that built the index."""
    m = load_manifest()
    if m is None:
        logger.warning("no index manifest at %s (index predates manifests); rebuild with "
                       "'gemprf-assistant index build --force' to record one", manifest_path())
        return
    if m.get("embedder") and m["embedder"] != embedder:
        raise RuntimeError(
            f"The index was built with embedder '{m['embedder']}' but the configured embedder is "
            f"'{embedder}'. Queries would search incompatible vectors. Either configure the matching "
            "embedding backend or rebuild: gemprf-assistant index build --force"
        )
    if m.get("chunking_version") != CHUNKING_VERSION:
        logger.warning("index chunking_version %s != current %s; consider "
                       "'gemprf-assistant index build --force'", m.get("chunking_version"), CHUNKING_VERSION)
