# Answer latency — where the time goes and how to keep it under 10s

Goal: keep a single `engine.ask()` answer under ~10s on the local Apple-Silicon /
Ollama setup, without regressing answer quality (the eval harness is the ground truth).

## Per-answer cost breakdown (qwen2.5:7b, e5-large-v2, bge-reranker-v2-m3, MPS)

Measured per stage on representative questions:

| stage                     | cost            | notes |
|---------------------------|-----------------|-------|
| embed query (e5-large-v2) | 0.1–1.3s        | negligible |
| parameter match           | <0.01s          | negligible |
| retrieve (Weaviate)       | 0.02–0.2s       | negligible |
| **rerank (cross-encoder)**| **5–12s @ pool 24** | dominant + most variable; scales with pool size |
| **LLM generate (qwen)**   | **prefill-bound**   | e.g. 4371-tok prompt → 9.4s prefill; ~150-tok decode only ~3s |

Two facts drive everything:

1. **Rerank dominates and scales with the pool.** It runs the bge-reranker-v2-m3
   cross-encoder over the candidate pool on MPS, contending with the LLM for the
   same GPU. Halving the pool roughly halves it.
2. **The LLM is prefill-bound, not decode-bound.** Decode of ~150 tokens is ~3s;
   the cost is processing the prompt. The prompt is large because evidence = 6 long
   chunks + appended parameter-relations (up to ~3k tokens). So the LLM lever is
   *prompt size*, not `max_tokens` (answers already finish well under the 768 cap).

Under GPU contention (e.g. another model loaded in Ollama, or an eval running in
parallel), both rerank and LLM throughput collapse and per-answer time can spike to
20–40s. For stable latency, don't run evals against the same Ollama/GPU you're
serving interactive answers from.

## What changed (default, no quality risk)

- **Rerank pool is now actually wired.** `GEMPRF_ASSISTANT_RERANK_POOL` was dead code
  — the engine hardcoded a pool of 24 and never read the env var, so the documented
  "pool 24→12" optimization was never in effect. The pool now reads the env var with
  a **default of 12** (`_rerank_pool_size()` in `rag/engine.py`), read per-call so it
  applies regardless of import order. Eval: hit@6 unchanged (14/15 == 14/15) vs pool 24.

  Effect: the "grid fit vs refine fit" synthesis question dropped from ~19s (pool 24,
  quiet) / 20–42s (contended) to **~7.7s** end-to-end at pool 12.

## Optional knobs (OFF by default — validate against eval before raising)

These trade answer quality for latency, so they default off. Flip one, run an eval
subset, confirm score/grounded hold, then keep it.

| env var | default | effect |
|---|---|---|
| `GEMPRF_ASSISTANT_RERANK_POOL` | `12` | rerank pool; lower = faster rerank, fewer rerank candidates |
| `GEMPRF_ASSISTANT_LLM_EVIDENCE_CHAR_CAP` | `0` (off) | per-chunk char cap on LLM evidence; cuts prefill (the dominant LLM cost). ~900 ≈ halves LLM-facing context on long-evidence questions. Affects the LLM prompt only — not retrieval, rerank, or citations |
| `GEMPRF_ASSISTANT_RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | swap to `BAAI/bge-reranker-base` (~2x faster, smaller) |
| `OLLAMA_KEEP_ALIVE` | server default ~5m | keep the answer model resident between queries (set server-side) |

### How to validate a knob

```bash
# baseline + candidate on a small subset, then compare score/grounded
GEMPRF_ASSISTANT_LLM_EVIDENCE_CHAR_CAP=900 \
  uv run python scripts/test_metric_fix.py   # or the eval entrypoint you use
```

Keep the change only if mean score and grounded-rate are within noise of baseline.
