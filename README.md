## Current results

```
category         n     avg   2-rate    grnd   hit@k   rec@k   lat(s)
---------------------------------------------------------------------
definitional    42    1.76      79%    100%     81%     81%    14.03
factual         45    1.73      82%    100%     76%     76%    13.16
negative        69    1.93      96%     99%       —       —    17.31
numerical       45    1.87      93%     98%     87%     87%    13.68
paraphrase      39    1.62      79%     97%     64%     64%    17.76
synthesis      164    1.88      92%     96%     95%     95%    14.66
overall        404    1.83      89%     98%     86%     86%    15.07
```

## Current Architecture

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

#### LLM provider

Set one of:

- `OPENAI_API_KEY` or `XAI_API_KEY` — For synthesis + judge.
- nothing — auto-falls back to Ollama (`ollama pull mistral-nemo:12b && ollama serve`). Force with `GEMPRF_ASSISTANT_LLM_PROVIDER=ollama`.

#### Run

```bash
python scripts/ingest.py                  
python -m gemprf_assistant.cli ask "What does nDCT do?"
# python -m gemprf_assistant.cli eval       
```
