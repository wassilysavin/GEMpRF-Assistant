## Setup

```bash
git clone --recurse-submodules https://github.com/wassilysavin/GEMpRF-Assistant.git
cd GEMpRF-Assistant
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
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

## Pipeline

```
INGEST
  curated sources (paper / website / repos / XML params)
        |
        v
  heading-aware splitter  -->  sections (parents) + chunks (leaves, overlap)
        |                              |
        |                              +--> embed --> Weaviate (GemPrfChunk, GemPrfSection)
        |
        +--> RDF knowledge graph (sources -- parameters -- sections -- chunks)


QUERY
  question
    |
    v
  rewrite: HyDE (gated by rare-anchor check)  OR  LLM keyword-rewrite
    |
    v
  embed once  +  ParameterMatcher (cosine vs. parameter specs)
    |
    v
  Hierarchical retrieval -- 4 rankings fused by RRF:
      (1) hybrid vector+BM25 over parent sections
      (2) hybrid over chunks, constrained to those parents
      (3) unconstrained chunk backfill
      (4) graph signal: KG 1-hop expansion of matched parameters
                        (seeds full weight, neighbours discounted)
    |
    v
  cross-encoder rerank  -->  per-source diversity cap  -->  top-k
    |
    v
  evidence floor?  -- no -->  "INSUFFICIENT_EVIDENCE" message
    | yes
    v
  LLM (OpenAI / xAI / Ollama) with system+human prompt
        - answer from evidence or emit INSUFFICIENT_EVIDENCE:
        - on failure: extractive fallback (stitch top chunks)
    |
    v
  strip [source.id] brackets  -->  AnswerResult { answer, citations, matched_params }
```
