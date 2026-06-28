## Current results

```
category         n     avg   2-rate    grnd   hit@k   rec@k   lat(s)
--------------------------------------------------------------------
definitional   10    1.80      90%    100%     90%     90%    25.66
factual        11    1.91      91%    100%     91%     91%    16.37
negative       13    2.00     100%    100%       —       —    88.76
numerical      11    2.00     100%    100%    100%    100%    45.05
paraphrase     10    1.70      70%    100%    100%    100%    13.90
synthesis      20    1.95      95%    100%    100%    100%    44.65
overall        75    1.91      92%    100%     97%     97%    41.57
```

## Current Architecture

```
INGEST
  curated sources (paper / website / repos / XML params)
        |
        v
  heading-aware splitter  -->  sections (parents) + chunks (leaves, overlap)
        |                              |
        |                              +--> embed (e5-large-v2; optional synthetic-question augmentation) --> Weaviate (GemPrfChunk, GemPrfSection)
        |
        +--> RDF knowledge graph (sources -- parameters -- sections -- chunks)


QUERY
  question
    |
    v
  rewrite: HyDE (gated by rare-anchor check)  OR  LLM keyword-rewrite
    |
    v
  embed once (e5 query prefix)  +  ParameterMatcher (cosine vs. parameter specs)
    |
    v
  Hierarchical retrieval -- 3 recall arms fused by one magnitude-preserving scoring pass:
      (1) hybrid vector+BM25 over chunks, constrained to top parent sections
      (2) unconstrained chunk backfill
      (3) graph recall: chunks tagged with matched parameters (KG 1-hop expanded)
    fused on per-arm min-max-normalised scores (+ parent-match & graph boosts), not RRF
    |
    v
  cross-encoder rerank  -->  per-source diversity cap  -->  top-k
    |
    v
  evidence floor?  -- no -->  relation fallback*  (else "INSUFFICIENT_EVIDENCE")
    | yes
    v
  LLM (OpenAI / xAI / Ollama) with system+human prompt
        - answer from evidence or emit INSUFFICIENT_EVIDENCE:
        - on LLM refusal: relation fallback*  (else "INSUFFICIENT_EVIDENCE")
        - on LLM error: retry, then extractive fallback (stitch top chunks)
    |
    v
  strip [source.id] brackets  -->  AnswerResult { answer, citations, matched_params }

  * relation fallback (refusal-only): instead of a dead-end refusal, return
    corpus-grounded parameter relations -- targeted to a parameter the question
    literally names (lexical match; embedding score does not separate on/off-topic),
    else a compact universal parameter-interaction matrix. Deterministic, no LLM;
    toggle via GEMPRF_ASSISTANT_RELATIONS.
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
