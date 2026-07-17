"""Central path resolution so the package works both from a source checkout and as an installed wheel."""
import os
from pathlib import Path

_APP = "gemprf-assistant"


def _checkout_root() -> Path | None:
    """The repo root when running from a source checkout (it holds the corpus submodules), else None."""
    checkout = Path(__file__).resolve().parents[2]
    return checkout if (checkout / "external").is_dir() else None


def corpus_root() -> Path:
    """Root holding the source corpus (external/, datasets/): env override, else the checkout root, else cwd."""
    env = os.getenv("GEMPRF_ASSISTANT_CORPUS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return _checkout_root() or Path.cwd()


def data_dir() -> Path:
    """Runtime state (weaviate index, kg.ttl, manifest, caches).

    Env override, else <checkout>/data for a maintainer checkout, else the OS user-data dir
    so an installed wheel keeps its index in one place instead of wherever it was launched.
    """
    env = os.getenv("GEMPRF_ASSISTANT_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    checkout = _checkout_root()
    if checkout is not None:
        return checkout / "data"
    from platformdirs import user_data_dir

    return Path(user_data_dir(_APP))


def user_config_path() -> Path:
    """Where `gemprf-assistant config set` persists the user's provider choice."""
    env = os.getenv("GEMPRF_ASSISTANT_CONFIG_FILE")
    if env:
        return Path(env).expanduser()
    from platformdirs import user_config_dir

    return Path(user_config_dir(_APP)) / "config.json"
