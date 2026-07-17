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
        |                              +--> embed (e5-large-v2) --> Weaviate (GemPrfChunk, GemPrfSection)
        |
        +--> RDF knowledge graph (sources -- parameters -- sections -- chunks)


QUERY  (engine.analyze -- stateless; per-session state lives in the conversation layer below)
  question
    |
    v
  follow-up condense (REPL only): LLM rewrites "what about it?" into a standalone question;
    a meaningful rewrite marks the turn a follow-up (a self-contained question passes through unchanged)
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
  cross-encoder rerank (pool default 12, GEMPRF_ASSISTANT_RERANK_POOL)  -->  per-source diversity cap  -->  top-k
    |
    v
  evidence floor?  -- no -->  relation fallback*  (else "INSUFFICIENT_EVIDENCE")
    | yes
    v
  LLM (OpenAI / xAI / Ollama) with system+human prompt
        (history block added only for genuine follow-ups -- as context, never as evidence; a
         self-contained question gets none, so stale prior turns can't bias its answer)
        - answer from evidence or emit INSUFFICIENT_EVIDENCE (matched anywhere, even when the model wraps it in a preamble)
        - on LLM refusal: relation fallback*  (else "INSUFFICIENT_EVIDENCE")
        - on LLM error: retry, then extractive fallback (stitch top chunks)
    |
    v
  strip [source.id] brackets  -->  AnswerResult { answer, citations, matched_params }


CONVERSATION LAYER  (REPL; engines stay stateless)
  rolling window of the last N answered turns (default 4; GEMPRF_ASSISTANT_HISTORY / _HISTORY_TURNS)
    - before retrieval: LLM condense of a follow-up into a standalone question (see QUERY);
      the condensed form also drives clarification's classify / plan / reformulate
    - in the answer prompt: rendered history block used as context only (never as evidence),
      and only when the turn is a genuine follow-up -- a self-contained question gets no history


CLARIFICATION INTAKE  (wraps analyze() in `ask` and the REPL: when the engine can't
  ground an answer, gather the user's situation instead of dead-ending on a refusal)

  classify the resolved (standalone) question -- one LLM word: ONTOPIC / VAGUE / OFFTOPIC
    (fallback when the gate is off: deterministic evidence-score floors for
     scope + overconfident-direct-answer detection)
    |
    +-- OFFTOPIC ------------------> refuse without asking
    +-- ONTOPIC -------------------> return the direct answer, or refuse honestly if ungrounded
    |                                (a specific/factual question is never interrogated)
    +-- VAGUE or ungrounded:
          |
          v
  plan 2-4 question-specific intake aspects from the failed analysis
    (LLM planner over failure reason + near-miss evidence; static checklist
     as fallback on planner failure; the user's goal is always the first aspect)
    |
    v
  intake loop (max GEMPRF_ASSISTANT_CLARIFY_MAX_ROUNDS): one clarifying
  question per aspect, fold each reply in, re-analyze -- stop as soon as it grounds
    (an aspect the conversation history already answers is folded in silently, not re-asked)
    |
    v
  reformulate: synthesize question + gathered context into ONE concrete
  GEM-pRF query, re-analyze
    |
    v
  drift guard: return the reformulated answer only if an LLM check says it
  addresses the ORIGINAL question
    |
    v
  mechanism fallback: still ungrounded --> present the doc-grounded parameter
  relations as a real answer conditioned on the gathered context, not a refusal

  * relation fallback (refusal-only): instead of a dead-end refusal, return
    corpus-grounded content -- a deterministic capability answer for pRF-model
    capability questions (2D Gaussian vs DoG/CSS), else relations for a parameter
    the question literally names (lexical match), else a confident relation-covered
    embedding match the question names, else a compact universal
    parameter-interaction matrix. Deterministic, no LLM;
    toggle via GEMPRF_ASSISTANT_RELATIONS.
```

## Quickstart

```bash
git clone --recurse-submodules https://github.com/wassilysavin/GEMpRF-Assistant.git
cd GEMpRF-Assistant
./run.sh
```

`run.sh` handles everything: installs dependencies into `.venv` (uses [uv](https://docs.astral.sh/uv/) if available, else pip), fetches the corpus submodules under `external/` if they are missing, downloads the embedding models, and gets the Weaviate index — a prebuilt snapshot from GitHub Releases when one is published (seconds), otherwise built locally on first run (10–20 min, one-time) — then drops you into the interactive REPL. Pass a question to answer it and exit:

```bash
./run.sh "What does nDCT do?"
```

Requirements: just Python >= 3.10 and git. For the LLM, either export `OPENAI_API_KEY` / `XAI_API_KEY` (also read from `.env`), or do nothing — the script installs [Ollama](https://ollama.com) if needed (Homebrew on macOS, official installer on Linux), starts it, and pulls `mistral-nemo:12b` (~7 GB, one-time).

## Manual setup

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
python -m gemprf_assistant.cli index build   # or: scripts/ingest.py                  
python -m gemprf_assistant.cli ask "What does nDCT do?"
python -m gemprf_assistant.cli repl       # interactive; follow-ups resolve via conversation history
# python -m gemprf_assistant.cli eval       
```

#### Tracing (optional)

Every answer can be traced back step-by-step (contextualize → query expansion → retrieval hits + scores → rerank → evidence selection → the exact LLM prompt/completion → fallbacks) in [Langfuse](https://langfuse.com):

```bash
pip install -e ".[trace]"
export LANGFUSE_PUBLIC_KEY=pk-... LANGFUSE_SECRET_KEY=sk-...
export LANGFUSE_HOST=https://cloud.langfuse.com   # or your self-hosted instance
```

With the keys set, `ask`/`repl`/`debug` print a per-answer trace URL, `ask --json` includes it as `trace_url`, and eval runs tag each case (`eval:<id>`) and link its trace in the `.review.md` report. Without the keys (or with `GEMPRF_ASSISTANT_TRACING=0`) tracing is a hard no-op.

#### Paths (installed / non-checkout use)

The package is relocatable: install the wheel anywhere and point it at data via env vars. From a source checkout both default to the repo automatically.

- `GEMPRF_ASSISTANT_CORPUS_DIR` — root holding `external/` and `datasets/` (default: the checkout root, else the current directory).
- `GEMPRF_ASSISTANT_DATA_DIR` — runtime state: Weaviate index, `kg.ttl`, caches (default: `./data`).

#### Prebuilt index snapshot

Installed users don't need the corpus or an ingest run — install a prebuilt index instead:

```bash
pip install gemprf-assistant
gemprf-assistant snapshot install <url-or-path>   # ~6 MB tar.gz into ./data (or GEMPRF_ASSISTANT_DATA_DIR)
gemprf-assistant ask "What does nDCT do?"
```

Queries must use the same embedding backend that built the index; `snapshot install` prints it from the snapshot manifest.

To publish a snapshot from a checkout with a built index (stop any running assistant first):

```bash
gemprf-assistant snapshot pack --out gemprf-index-snapshot.tar.gz   # then attach to a GitHub Release
```
