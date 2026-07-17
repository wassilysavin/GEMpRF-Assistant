"""App logging + per-stage timing: every degradation logs a warning instead of vanishing."""
import logging
import sys
import time
from contextlib import contextmanager

from .config import get_settings

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    """Module logger; first call installs a stderr handler (level via GEMPRF_ASSISTANT_LOG_LEVEL, default WARNING)."""
    global _CONFIGURED
    if not _CONFIGURED:
        level = get_settings().log_level
        root = logging.getLogger("gemprf_assistant")
        if not root.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
            root.addHandler(handler)
        root.setLevel(getattr(logging, level, logging.WARNING))
        root.propagate = False
        _CONFIGURED = True
    return logging.getLogger(name)


@contextmanager
def stage_timer(timings: dict[str, float] | None, stage: str):
    """Record the stage's wall-clock seconds into `timings` (no-op when timings is None)."""
    start = time.perf_counter()
    try:
        yield
    finally:
        if timings is not None:
            timings[stage] = round(time.perf_counter() - start, 3)
