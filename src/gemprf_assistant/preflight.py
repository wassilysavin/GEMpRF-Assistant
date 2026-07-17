"""Startup preflight: instant model-size gate + one-shot local Ollama speed benchmark; suggest the hosted chat / xAI API when either is insufficient."""
import json
import os
import platform
import re
import shutil
import sys
import urllib.request
from pathlib import Path

from .config import get_settings

MIN_OK_TOK_S = 8.0
MIN_FAST_TOK_S = 15.0
MIN_RAM_GB = 8.0
# Sub-4B models fail grounded-reasoning probes (rule application, arithmetic, negation) that 7B+ pass.
MIN_PARAMS_B = 4.0

_BENCH_PROMPT = "Briefly explain what a population receptive field is."
_BENCH_TOKENS = 64
_SUGGESTION = (
    "use the chat on the GEM-pRF website (https://gemprf.github.io), or answer via the xAI API "
    "instead: set XAI_API_KEY and run `gemprf-assistant config set llm_provider xai`."
)


def uses_local_ollama() -> bool:
    """True when build_chat_llm would resolve to the local Ollama provider."""
    return get_settings().resolve_llm_provider() == "ollama"


def total_ram_gb() -> float | None:
    """Total physical RAM in GB (macOS/Linux), or None when undeterminable."""
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except (AttributeError, ValueError, OSError):
        return None


def has_accelerator() -> bool:
    """True on Apple Silicon or when an NVIDIA GPU driver is present."""
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return True
    return shutil.which("nvidia-smi") is not None


def verdict(tok_s: float) -> str:
    """Classify a measured generation speed: 'ok', 'slow' (usable), or 'bad' (recommend external)."""
    if tok_s < MIN_OK_TOK_S:
        return "bad"
    if tok_s < MIN_FAST_TOK_S:
        return "slow"
    return "ok"


def _ollama_native_base() -> str:
    return get_settings().ollama_base_url.rstrip("/").removesuffix("/v1")


def _ollama_generate(model: str, prompt: str, timeout: float = 300.0) -> dict | None:
    """One non-streaming completion via the native Ollama API, or None when unreachable/failed."""
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": _BENCH_TOKENS, "temperature": 0},
        }
    ).encode()
    request = urllib.request.Request(
        _ollama_native_base() + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except Exception:
        return None


def benchmark_tok_s(model: str, timeout: float = 300.0) -> float | None:
    """Generation speed (tokens/sec) from one short Ollama completion, or None when unreachable."""
    data = _ollama_generate(model, _BENCH_PROMPT, timeout=timeout)
    if data is None:
        return None
    duration_s = data.get("eval_duration", 0) / 1e9
    count = data.get("eval_count", 0)
    if duration_s <= 0 or not count:
        return None
    return count / duration_s


def parse_params_b(size: str) -> float | None:
    """Billions of parameters from an Ollama parameter_size string like '7.6B' or '494M', or None."""
    match = re.fullmatch(r"([\d.]+)\s*([MB])", size.strip().upper())
    if not match:
        return None
    value = float(match.group(1))
    return value / 1000 if match.group(2) == "M" else value


def ollama_model_tags(timeout: float = 5.0) -> list[dict] | None:
    """Raw /api/tags model entries (name + details incl. parameter_size), or None when Ollama is unreachable."""
    try:
        with urllib.request.urlopen(_ollama_native_base() + "/api/tags", timeout=timeout) as response:
            data = json.loads(response.read())
    except Exception:
        return None
    return [m for m in data.get("models", []) if m.get("name")]


def installed_ollama_models(timeout: float = 5.0) -> list[str] | None:
    """Names of locally installed Ollama models, or None when Ollama is unreachable."""
    tags = ollama_model_tags(timeout=timeout)
    return None if tags is None else [m["name"] for m in tags]


def model_params_b(model: str, timeout: float = 5.0) -> float | None:
    """Model size in billions of parameters from /api/show (instant, no generation), or None when unavailable."""
    request = urllib.request.Request(
        _ollama_native_base() + "/api/show",
        data=json.dumps({"model": model}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read())
    except Exception:
        return None
    return parse_params_b(str(data.get("details", {}).get("parameter_size", "")))


def _cache_path() -> Path:
    cache_root = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return cache_root / "gemprf_assistant" / "preflight.json"


def _load_cache() -> dict:
    try:
        return json.loads(_cache_path().read_text())
    except Exception:
        return {}


def _save_cache_entry(model: str, entry: dict) -> None:
    cache = _load_cache()
    cache[model] = entry
    try:
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, indent=2))
    except OSError:
        pass


def _warn(message: str) -> None:
    print(f"[preflight] {message}", file=sys.stderr)


def cached_entry(model: str) -> dict | None:
    """The cached preflight result for a model, if any."""
    return _load_cache().get(model)


def _report(model: str, entry: dict) -> None:
    kind, tok_s = entry.get("verdict"), entry.get("tok_s")
    if kind == "ok":
        return
    if kind == "bad" and tok_s is None:
        _warn(f"this machine is not suited for local inference ({entry.get('reason')}); {_SUGGESTION}")
    elif kind == "bad":
        _warn(f"local {model} benchmarked at {tok_s:.1f} tokens/s — answers will take minutes; {_SUGGESTION}")
    elif kind == "slow":
        _warn(f"local {model} benchmarked at {tok_s:.1f} tokens/s — usable but slow; for faster answers, {_SUGGESTION}")


def _check_model_strength(model: str) -> None:
    """Instant size gate from Ollama metadata: warn when the model is too small for reliable grounded answers."""
    params_b = model_params_b(model)
    if params_b is not None and params_b < MIN_PARAMS_B:
        _warn(
            f"local {model} has only {params_b:.1f}B parameters — likely not strong enough for "
            f"reliable grounded answers; prefer a {MIN_PARAMS_B:.0f}B+ model, {_SUGGESTION}"
        )


def check_local_llm() -> None:
    """Warn when the local model is too small (instant metadata check) or the machine too slow (benchmarked once per model, then cached); never raises or blocks startup."""
    if not get_settings().preflight_enabled:
        return
    if not uses_local_ollama():
        return
    model = get_settings().ollama_model
    _check_model_strength(model)
    cached = _load_cache().get(model)
    if cached is not None:
        _report(model, cached)
        return
    ram = total_ram_gb()
    if ram is not None and ram < MIN_RAM_GB:
        entry = {"verdict": "bad", "tok_s": None, "reason": f"only {ram:.0f} GB RAM"}
        _save_cache_entry(model, entry)
        _report(model, entry)
        return
    hint = "" if has_accelerator() else " (no GPU/Apple Silicon detected, this may take a while)"
    _warn(f"benchmarking local {model} once to check this machine's speed{hint}...")
    tok_s = benchmark_tok_s(model)
    if tok_s is None:
        _warn(f"could not reach Ollama to benchmark {model}; if local inference is unavailable, {_SUGGESTION}")
        return
    entry = {"verdict": verdict(tok_s), "tok_s": round(tok_s, 1)}  # type: ignore[dict-item]
    _save_cache_entry(model, entry)
    _report(model, entry)
    if entry["verdict"] == "ok":
        _warn(f"local {model} runs at {tok_s:.1f} tokens/s — good enough for local use.")
