#!/usr/bin/env bash
# One-command bootstrap: sets up submodules, venv, models, and the LLM, then starts the assistant.
# Usage: ./run.sh              (interactive REPL)
#        ./run.sh "question"   (answer one question and exit)
set -euo pipefail
cd "$(dirname "$0")"

info() { printf '\033[1;34m[run.sh]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[run.sh]\033[0m %s\n' "$*" >&2; exit 1; }

# --- Python >= 3.10 ---
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
    for candidate in python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1 \
           && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    done
fi
[ -n "$PYTHON" ] || die "Python >= 3.10 not found. Install it (e.g. https://www.python.org) and re-run."

# --- Submodules (corpus sources under external/) ---
if [ -e .git ] && [ ! -f external/GEMpRF-DemoKit/README.md ]; then
    info "Fetching corpus submodules under external/ ..."
    git submodule update --init --recursive
fi

# --- Virtualenv + install (re-installs only when pyproject.toml changes) ---
VENV=".venv"
STAMP="$VENV/.run-sh-installed"
if [ ! -f "$STAMP" ] || [ pyproject.toml -nt "$STAMP" ]; then
    if command -v uv >/dev/null 2>&1; then
        info "Installing dependencies with uv ..."
        uv venv --quiet --allow-existing --python "$PYTHON" "$VENV"
        uv pip install --quiet --python "$VENV/bin/python" -e .
    else
        info "Installing dependencies with pip (this can take a few minutes) ..."
        [ -d "$VENV" ] || "$PYTHON" -m venv "$VENV"
        "$VENV/bin/pip" install --quiet --upgrade pip
        "$VENV/bin/pip" install --quiet -e .
    fi
    touch "$STAMP"
fi

# --- LLM provider: use an API key if present, otherwise local Ollama ---
if [ -f .env ]; then
    # export .env so the ollama checks below see the same keys the app will
    set -a; . ./.env; set +a
fi
PROVIDER="${GEMPRF_ASSISTANT_LLM_PROVIDER:-}"
if [ -z "${OPENAI_API_KEY:-}${XAI_API_KEY:-}" ] || [ "$PROVIDER" = "ollama" ]; then
    OLLAMA_MODEL="${GEMPRF_ASSISTANT_OLLAMA_MODEL:-mistral-nemo:12b}"
    if ! command -v ollama >/dev/null 2>&1; then
        info "No API key set and Ollama not found — installing Ollama (local LLM runtime) ..."
        case "$(uname -s)" in
            Darwin)
                command -v brew >/dev/null 2>&1 \
                    || die "Homebrew not found. Install Ollama from https://ollama.com/download or export an OPENAI_API_KEY / XAI_API_KEY."
                brew install ollama
                ;;
            Linux)
                # official installer; may prompt for sudo
                curl -fsSL https://ollama.com/install.sh | sh
                ;;
            *)
                die "Unsupported OS for Ollama auto-install. Install it from https://ollama.com/download or export an OPENAI_API_KEY / XAI_API_KEY."
                ;;
        esac
        command -v ollama >/dev/null 2>&1 || die "Ollama install did not complete. Install it manually: https://ollama.com/download"
    fi
    if ! curl -fs "${GEMPRF_ASSISTANT_OLLAMA_BASE_URL:-http://localhost:11434/v1}/models" >/dev/null 2>&1; then
        info "Starting Ollama server in the background ..."
        (ollama serve >/dev/null 2>&1 &)
        sleep 3
    fi
    # grep without -q: -q exits early and SIGPIPEs ollama, failing the pipeline under pipefail
    if ! ollama list 2>/dev/null | grep "^${OLLAMA_MODEL%%:*}" >/dev/null; then
        info "Pulling local LLM $OLLAMA_MODEL (one-time, several GB) ..."
        ollama pull "$OLLAMA_MODEL"
    fi
fi

# --- First run: try a prebuilt index snapshot, else build the index locally ---
export GEMPRF_ASSISTANT_EMBEDDING_ALLOW_DOWNLOAD=1
INDEX_DIR="${GEMPRF_ASSISTANT_WEAVIATE_PATH:-data/weaviate}"
# ${VAR-default} (no colon) so setting it to an empty string disables the snapshot attempt
SNAPSHOT_URL="${GEMPRF_ASSISTANT_SNAPSHOT_URL-https://github.com/wassilysavin/GEMpRF-Assistant/releases/latest/download/gemprf-index-snapshot.tar.gz}"
if [ ! -d "$INDEX_DIR" ] && [ -n "$SNAPSHOT_URL" ]; then
    info "Looking for a prebuilt index snapshot ..."
    "$VENV/bin/python" -m gemprf_assistant.cli snapshot install "$SNAPSHOT_URL" 2>/dev/null \
        || info "No snapshot available — building the index locally instead."
fi
if [ ! -d "$INDEX_DIR" ]; then
    info "First run: downloading embedding models and ingesting the corpus (10-20 min) ..."
fi

if [ "$#" -gt 0 ]; then
    exec "$VENV/bin/python" -m gemprf_assistant.cli ask "$@"
else
    exec "$VENV/bin/python" -m gemprf_assistant.cli repl
fi
