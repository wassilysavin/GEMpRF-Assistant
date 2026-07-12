"""Central path resolution so the package works both from a source checkout and as an installed wheel."""
import os
from pathlib import Path


def corpus_root() -> Path:
    """Root holding the source corpus (external/, datasets/): env override, else the checkout root, else cwd."""
    env = os.getenv("GEMPRF_ASSISTANT_CORPUS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "external").is_dir():
        return checkout
    return Path.cwd()


def data_dir() -> Path:
    """Runtime-state dir (weaviate index, kg.ttl, caches): env override, else ./data."""
    env = os.getenv("GEMPRF_ASSISTANT_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd() / "data"
