## Setup

```bash
git clone --recurse-submodules https://github.com/wassilysavin/shenzhou3.git
cd shenzhou3
pip install -e .
```

`--recurse-submodules` pulls in the GEM-pRF and DemoKit GitHub projects under `external/`, which the ingest pipeline reads.

## LLM provider

Set one of:

- `OPENAI_API_KEY` or `XAI_API_KEY` — For synthesis + judge.
- nothing — auto-falls back to Ollama (`ollama pull mistral-nemo:12b && ollama serve`). Force with `GEMPRF_ASSISTANT_LLM_PROVIDER=ollama`.

## Run

```bash
python scripts/ingest.py                  
python -m gemprf_assistant.cli ask "What does nDCT do?"
# python -m gemprf_assistant.cli eval       
```
