"""Optional Langfuse tracing: every pipeline step becomes a span so an answer can be traced back.

Enabled only when the `langfuse` package is installed and LANGFUSE_PUBLIC_KEY /
LANGFUSE_SECRET_KEY are set (LANGFUSE_HOST selects the server); otherwise every
helper is a silent no-op. GEMPRF_ASSISTANT_TRACING=0 is the kill switch.
"""
import os
from contextlib import contextmanager
from typing import Any

_STATE: dict[str, Any] = {"checked": False, "client": None, "handler": None, "url_broken": False}


def _requested() -> bool:
    """True when the kill switch is off and both Langfuse keys are present."""
    if os.getenv("GEMPRF_ASSISTANT_TRACING", "1").strip() == "0":
        return False
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def _client():
    """Lazily build the singleton Langfuse client (None when disabled or unavailable)."""
    if not _STATE["checked"]:
        _STATE["checked"] = True
        if _requested():
            try:
                from langfuse import get_client
                from langfuse.langchain import CallbackHandler

                _STATE["client"] = get_client()
                _STATE["handler"] = CallbackHandler()
            except Exception:
                _STATE["client"] = None
                _STATE["handler"] = None
    return _STATE["client"]


def _reset() -> None:
    """Drop the cached client so the next call re-reads the environment (tests)."""
    _STATE.update(checked=False, client=None, handler=None, url_broken=False)


def enabled() -> bool:
    return _client() is not None


def langchain_config() -> dict:
    """invoke() config carrying the Langfuse callback so LLM calls log as generations ({} when off)."""
    _client()
    return {"callbacks": [_STATE["handler"]]} if _STATE["handler"] is not None else {}


def invoke_kwargs() -> dict:
    """Splat into llm.invoke(...): adds the Langfuse config only when tracing is on, so non-Runnable test fakes keep working."""
    config = langchain_config()
    return {"config": config} if config else {}


class _NoopSpan:
    """Stand-in observation when tracing is off; absorbs every update call."""

    def update(self, **kwargs):
        return self


@contextmanager
def span(name: str, as_type: str = "span", **kwargs):
    """Open a named observation around a pipeline step (yields a no-op stub when tracing is off)."""
    client = _client()
    if client is None:
        yield _NoopSpan()
        return
    with client.start_as_current_observation(name=name, as_type=as_type, **kwargs) as obs:
        yield obs


@contextmanager
def trace_attributes(**kwargs):
    """Propagate trace-level attributes (session_id, tags, trace_name) onto nested observations."""
    if _client() is None:
        yield
        return
    from langfuse import propagate_attributes

    with propagate_attributes(**kwargs):
        yield


def current_trace_url() -> str | None:
    """URL of the trace active right now (call inside a span; None when tracing is off)."""
    client = _client()
    if client is None or _STATE["url_broken"]:
        return None
    try:
        trace_id = client.get_current_trace_id()
        if not trace_id:
            return None
        url = client.get_trace_url(trace_id=trace_id)
    except Exception:
        url = None
    if url is None:
        _STATE["url_broken"] = True  # project-id lookup failed; don't re-pay its API timeout every query
    return url


def flush() -> None:
    """Block until queued spans are exported (call before process exit)."""
    if _STATE["client"] is not None:
        try:
            _STATE["client"].flush()
        except Exception:
            pass
