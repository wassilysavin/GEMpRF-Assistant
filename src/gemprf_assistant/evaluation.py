import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_PATH = ROOT / "datasets" / "paper_eval_qa.jsonl"
DEFAULT_RESULTS_PATH = ROOT / "datasets" / "paper_eval_results.json"


@dataclass
class CaseResult:
    id: str
    type: str
    question: str
    gold_answer: str
    model_answer: str
    retrieved_source_ids: list[str]
    retrieved_previews: list[str]
    retrieval_hit: bool | None
    retrieval_rank: int | None
    recall_at_k: float | None = None
    precision_at_k: float | None = None
    judge_score: int | None = None
    judge_grounded: bool | None = None
    judge_rationale: str | None = None
    # Answer-quality signal (judge-derived), kept separate from retrieval_hit so
    # the two are never conflated. score >= 1 AND grounded.
    answer_correct: bool | None = None
    # When repeats>1, the per-run judge scores (answer is regenerated each run).
    # judge_score holds the modal score; this exposes the generation variance.
    judge_score_runs: list | None = None
    ragas_faithfulness: float | None = None
    ragas_answer_relevancy: float | None = None
    ragas_context_precision: float | None = None
    ragas_context_recall: float | None = None
    latency_s: float = 0.0
    engine_status: str = ""
    used_llm: bool = False
    rerank_used: bool = False


def load_eval_set(path: Path = DEFAULT_EVAL_PATH) -> list[dict]:
    """Read a JSONL eval file into a list of case dicts.
    """
    cases = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _norm(s: str) -> str:
    """Lowercase + collapse whitespace so gold-substring matching is robust to
    line-wrapping and casing in chunk text (avoids false retrieval misses)."""
    return re.sub(r"\s+", " ", s or "").strip().lower()


def score_retrieval(case: dict, evidence: list[dict]) -> tuple[bool | None, int | None]:
    # Only true negatives (expected refusals) have no gold to match. Synthesis
    # cases DO carry a gold_substring that should appear in a retrieved chunk,
    # so they get a real retrieval signal here — answer quality is judged
    # separately via answer_correct (see evaluate()).
    if case["type"] == "negative":
        return None, None
    needle = _norm(case.get("gold_substring") or "")
    gold_src = set(case.get("gold_source_ids") or [])
    if not needle and not gold_src:
        return None, None
    # A hit = the gold chunk was retrieved, by EITHER the gold substring appearing
    # in a chunk OR a retrieved chunk coming from a gold source. The source-id match
    # is what makes synthesis/paraphrase fair: their answers paraphrase across chunks,
    # so the verbatim substring often isn't present even when the right chunk is.
    for rank, item in enumerate(evidence, start=1):
        if (needle and needle in _norm(item.get("text", ""))) or (item.get("source_id") in gold_src):
            return True, rank
    return False, None


def score_recall_precision(
    hit: bool | None, k: int
) -> tuple[float | None, float | None]:
    if hit is None:
        return None, None
    if k <= 0:
        return None, None
    return (1.0 if hit else 0.0, (1.0 / k) if hit else 0.0)


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

_SOURCE_TYPE_TAG = {
    "paper": "paper",
    "website": "docs",
    "repo": "code",
    "code": "code",
    "github": "code",
    "demokit": "DemoKit",
}

# Pulls a function or class signature out of a code chunk's preview when
# the chunker didn't prepend a heading. Used as the fallback 
_DEF_SIG_RE = re.compile(r"\b(def|class)\s+(\w+)\s*[\(:]", re.IGNORECASE)


def _source_kind(source_id: str) -> str:
    return _SOURCE_TYPE_TAG.get(source_id.split(".", 1)[0], "source")


def _source_location_hint(preview: str) -> str:
    """Extract a one-line "where in the source" hint from a chunk preview.
    """
    if not preview:
        return ""
    if "\n\n" in preview:
        head = " ".join(preview.split("\n\n", 1)[0].split())
        if 0 < len(head) <= 100:
            return head
    match = _DEF_SIG_RE.search(preview[:200])
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return ""


def _render_sources_block(source_ids, previews, sources_by_id) -> str:
    """Render the per-case "Sources used:" bullet list for the review markdown.
    """
    lines = ["Sources used:"]
    seen: set[tuple[str, str]] = set()
    for sid, prev in zip(source_ids, previews or []):
        loc = _source_location_hint(prev or "")
        key = (sid, loc)
        if key in seen:
            continue
        seen.add(key)
        title = getattr(sources_by_id.get(sid), "title", None) or sid
        if loc and loc.lower() != title.lower():
            lines.append(f"    - {title} ({_source_kind(sid)}) — {loc}")
        else:
            lines.append(f"    - {title} ({_source_kind(sid)})")
    return "\n".join(lines)


def parse_judge_response(text: str) -> dict | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(stripped)
        if not m:
            return None
        try:
            payload = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


def build_judge():
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        return None
    provider = os.getenv("GEMPRF_ASSISTANT_LLM_PROVIDER", "").strip().lower()
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_xai = bool(os.getenv("XAI_API_KEY"))
    if provider == "ollama" or (not provider and not has_openai and not has_xai):
        return ChatOpenAI(
            model=os.getenv("GEMPRF_ASSISTANT_OLLAMA_MODEL", "mistral-nemo:12b"),
            api_key=os.getenv("GEMPRF_ASSISTANT_OLLAMA_API_KEY", "ollama"),
            base_url=os.getenv("GEMPRF_ASSISTANT_OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            temperature=0,
            max_tokens=int(os.getenv("GEMPRF_ASSISTANT_OLLAMA_MAX_TOKENS", "768")),
        )
    if provider == "xai" or (not provider and has_xai and not has_openai):
        if not has_xai:
            return None
        return ChatOpenAI(
            model=os.getenv("GEMPRF_ASSISTANT_XAI_MODEL", "grok-4.3"),
            api_key=os.getenv("XAI_API_KEY"),
            base_url=os.getenv("GEMPRF_ASSISTANT_XAI_BASE_URL", "https://api.x.ai/v1"),
            temperature=0,
        )
    if not has_openai:
        return None
    return ChatOpenAI(model=os.getenv("GEMPRF_ASSISTANT_MODEL", "gpt-4o-mini"), temperature=0)


def judge_case(llm, case: dict, model_answer: str, evidence: list[dict]) -> dict:
    """Score one model answer with the LLM judge, returns {score, grounded, rationale}.
    """
    from langchain_core.prompts import ChatPromptTemplate
    from .rag.prompts import JUDGE_SYSTEM_PROMPT

    context = "\n\n".join(f"[{e['source_id']}] {e['text']}" for e in evidence) or "(no context retrieved)"
    user = (
        f"Question: {case['question']}\n\n"
        f"Question type: {case['type']}\n\n"
        f"Reference answer: {case['gold_answer']}\n\n"
        f"Model answer: {model_answer}\n\n"
        f"Retrieved context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([("system", JUDGE_SYSTEM_PROMPT), ("human", "{user}")])
    try:
        response = (prompt | llm).invoke({"user": user})
        payload = parse_judge_response(str(response.content))
    except Exception as exc:
        return {"score": None, "grounded": None, "rationale": f"judge_error: {exc}"}
    if not payload:
        return {"score": None, "grounded": None, "rationale": "unparseable_judge_response"}
    score = payload.get("score")
    return {
        "score": int(score) if isinstance(score, (int, float)) else None,
        "grounded": bool(payload["grounded"]) if "grounded" in payload else None,
        "rationale": str(payload.get("rationale") or "").strip() or None,
    }


class _EngineEmbeddingsAdapter:

    def __init__(self, backend) -> None:
        self._backend = backend

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._backend.embed_texts(list(texts)).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._backend.embed_texts([text])[0].tolist()


def build_ragas_metrics(*, llm=None, embedding_backend=None) -> dict | None:
    """Build the RAGAS metric set (Faithfulness + Context Recall), or None
    """
    if llm is None or embedding_backend is None:
        return None
    try:
        try:
            import nest_asyncio 

            nest_asyncio.apply = lambda *a, **kw: None 
        except Exception:
            pass
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import ContextRecall, Faithfulness
    except Exception:
        return None
    wrapped_llm = LangchainLLMWrapper(llm)
    LangchainEmbeddingsWrapper(_EngineEmbeddingsAdapter(embedding_backend))
    return {
        "faithfulness": Faithfulness(llm=wrapped_llm),
        "context_recall": ContextRecall(llm=wrapped_llm),
    }


def ragas_score_case(
    metrics: dict, case: dict, model_answer: str, evidence: list[dict]
) -> dict:
    """Run each configured RAGAS metric on one case, returns {key: float | None}
    """
    import asyncio

    from ragas.dataset_schema import SingleTurnSample

    answer = (model_answer or "").strip()
    contexts = [e.get("text", "") for e in evidence]
    if not answer or not contexts:
        return {k: None for k in metrics}
    reference = (case.get("gold_answer") or "").strip() or None
    sample = SingleTurnSample(
        user_input=case["question"],
        response=answer,
        retrieved_contexts=contexts,
        reference=reference,
    )
    needs_reference = {"context_precision", "context_recall"}
    out: dict = {}
    for key, metric in metrics.items():
        if key in needs_reference and not reference:
            out[key] = None
            continue
        try:
            value = asyncio.run(metric.single_turn_ascore(sample))
        except Exception:
            value = None
        if value is None or (isinstance(value, float) and value != value):
            out[key] = None
        else:
            out[key] = float(value)
    return out


def aggregate(results: Iterable[CaseResult]) -> dict:
    results = list(results)
    by_type: dict[str, list[CaseResult]] = {}
    for r in results:
        by_type.setdefault(r.type, []).append(r)

    _JUDGE_GRADED_TYPES = {"synthesis"}

    def summarize(group: list[CaseResult]) -> dict:
        hits = [r.retrieval_hit for r in group if r.retrieval_hit is not None]
        rank_pool = [
            r for r in group
            if r.retrieval_hit is not None and r.type not in _JUDGE_GRADED_TYPES
        ]
        ranks = [1.0 / r.retrieval_rank for r in rank_pool if r.retrieval_rank]
        recalls = [r.recall_at_k for r in group if r.recall_at_k is not None]
        precisions = [r.precision_at_k for r in group if r.precision_at_k is not None]
        scores = [r.judge_score for r in group if r.judge_score is not None]
        grounded = [r.judge_grounded for r in group if r.judge_grounded is not None]
        acorr = [r.answer_correct for r in group if r.answer_correct is not None]
        faith = [r.ragas_faithfulness for r in group if r.ragas_faithfulness is not None]
        relev = [r.ragas_answer_relevancy for r in group if r.ragas_answer_relevancy is not None]
        cprec = [r.ragas_context_precision for r in group if r.ragas_context_precision is not None]
        crec = [r.ragas_context_recall for r in group if r.ragas_context_recall is not None]
        return {
            "n": len(group),
            "hit_at_k": (sum(1 for h in hits if h) / len(hits)) if hits else None,
            "recall_at_k": mean(recalls) if recalls else None,
            "precision_at_k": mean(precisions) if precisions else None,
            "mrr": (sum(ranks) / len(rank_pool)) if rank_pool else None,
            "avg_score": (mean(scores)) if scores else None,
            "score_2_rate": (sum(1 for s in scores if s == 2) / len(scores)) if scores else None,
            "grounded_rate": (sum(1 for g in grounded if g) / len(grounded)) if grounded else None,
            "answer_correct_rate": (sum(1 for a in acorr if a) / len(acorr)) if acorr else None,
            "faithfulness": mean(faith) if faith else None,
            "answer_relevancy": mean(relev) if relev else None,
            "context_precision": mean(cprec) if cprec else None,
            "context_recall": mean(crec) if crec else None,
            "avg_latency_s": mean(r.latency_s for r in group) if group else 0.0,
        }

    return {
        "overall": summarize(results),
        "by_type": {t: summarize(g) for t, g in sorted(by_type.items())},
    }


def format_table(agg: dict) -> str:
    """Render an aggregate() as a text table.
    """
    header = (
        f"{'category':<14}{'n':>4}{'hit@k':>8}"
        f"{'mrr':>7}{'avg':>7}{'2-rate':>9}{'acorr':>8}{'grnd':>8}{'faith':>8}{'crec':>8}{'lat(s)':>9}"
    )
    rows = [header, "-" * len(header)]
    for name, stats in sorted(agg["by_type"].items()) + [("overall", agg["overall"])]:
        def fmt(v, pct=False):
            if v is None:
                return f"{'—':>1}"
            return f"{v*100:.0f}%" if pct else f"{v:.2f}"
        rows.append(
            f"{name:<14}"
            f"{stats['n']:>4}"
            f"{fmt(stats['hit_at_k'], pct=True):>8}"
            f"{fmt(stats['mrr']):>7}"
            f"{fmt(stats['avg_score']):>7}"
            f"{fmt(stats['score_2_rate'], pct=True):>9}"
            f"{fmt(stats.get('answer_correct_rate'), pct=True):>8}"
            f"{fmt(stats['grounded_rate'], pct=True):>8}"
            f"{fmt(stats['faithfulness']):>8}"
            f"{fmt(stats.get('context_recall')):>8}"
            f"{stats['avg_latency_s']:>9.2f}"
        )
    return "\n".join(rows)


def evaluate(
    engine,
    *,
    cases: list[dict] | None = None,
    top_k: int = 6,
    judge=None,
    no_judge: bool = False,
    ragas_metrics: dict | None = None,
    enable_ragas: bool = False,
    repeats: int = 1,
    on_progress=None,
) -> dict:
    cases = cases if cases is not None else load_eval_set()
    if not no_judge and judge is None:
        judge = build_judge()
    if enable_ragas and ragas_metrics is None:
        ragas_metrics = build_ragas_metrics(
            llm=judge,
            embedding_backend=getattr(engine, "embedding_backend", None),
        )

    results: list[CaseResult] = []
    for i, case in enumerate(cases, 1):
        start = time.monotonic()
        ans = engine.ask_dict(case["question"], top_k=top_k)
        latency = time.monotonic() - start

        evidence = ans["evidence"]
        hit, rank = score_retrieval(case, evidence)
        recall, precision = score_recall_precision(hit, top_k)
        case_result = CaseResult(
            id=case["id"],
            type=case["type"],
            question=case["question"],
            gold_answer=case["gold_answer"],
            model_answer=ans["answer"],
            retrieved_source_ids=[e["source_id"] for e in evidence],
            retrieved_previews=[e["text"][:180] for e in evidence],
            retrieval_hit=hit,
            retrieval_rank=rank,
            recall_at_k=recall,
            precision_at_k=precision,
            latency_s=float(latency),
            engine_status=ans["status"],
            used_llm=bool(ans.get("used_llm")),
            rerank_used=bool(ans.get("rerank_used")),
        )
        if judge is not None:
            j = judge_case(judge, case, ans["answer"], evidence)
            # repeats>1 de-noises the (noisy) answer generation: regenerate +
            # rejudge k-1 more times and take the modal score. Retrieval is
            # deterministic, so only the generation/judge step is repeated.
            if repeats > 1:
                runs = [j]
                for _ in range(repeats - 1):
                    extra = engine.ask_dict(case["question"], top_k=top_k)
                    runs.append(judge_case(judge, case, extra["answer"], extra["evidence"]))
                scored = [r["score"] for r in runs if r["score"] is not None]
                case_result.judge_score_runs = [r["score"] for r in runs]
                if scored:
                    mode = max(set(scored), key=scored.count)
                    j = next(r for r in runs if r["score"] == mode)
            case_result.judge_score = j["score"]
            case_result.judge_grounded = j["grounded"]
            case_result.judge_rationale = j["rationale"]
            # Answer quality is a generation metric — keep it OUT of retrieval_hit.
            # retrieval_hit now reflects real chunk retrieval (incl. synthesis,
            # via score_retrieval); answer_correct carries the judge verdict.
            if case_result.judge_score is not None:
                case_result.answer_correct = (
                    case_result.judge_score >= 1 and bool(case_result.judge_grounded)
                )
        if ragas_metrics is not None:
            r = ragas_score_case(ragas_metrics, case, ans["answer"], evidence)
            # Refusals contain no factual claims, so Faithfulness has nothing
            # to extract
            if ans["status"] != "insufficient_evidence":
                case_result.ragas_faithfulness = r.get("faithfulness")
            case_result.ragas_answer_relevancy = r.get("answer_relevancy")
            case_result.ragas_context_precision = r.get("context_precision")
            case_result.ragas_context_recall = r.get("context_recall")
        results.append(case_result)
        if on_progress is not None:
            on_progress(i, len(cases), case_result)

    return {
        "top_k": top_k,
        "judge_enabled": judge is not None,
        "ragas_enabled": ragas_metrics is not None,
        "aggregate": aggregate(results),
        "cases": [asdict(r) for r in results],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the eval.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N cases.")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--repeat", type=int, default=1,
                        help="Regenerate+rejudge each case N times and take the modal "
                             "judge score (de-noises grok answer-generation variance).")
    parser.add_argument(
        "--ragas",
        action="store_true",
        help="Score each case with RAGAS faithfulness + answer relevancy "
        "(uses the judge LLM and the embedding backend)",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_EVAL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS_PATH)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(ROOT / "src"))
    from gemprf_assistant.rag.engine import GraphRagEngine

    cases = load_eval_set(args.dataset)
    if args.offset:
        cases = cases[args.offset:]
    if args.limit:
        cases = cases[: args.limit]
    try:
        _ds = args.dataset.resolve().relative_to(ROOT)
    except ValueError:
        _ds = args.dataset
    print(f"loaded {len(cases)} cases from {_ds}")

    engine = GraphRagEngine()
    sources_by_id = engine.sources

    checkpoint_path = args.output.with_suffix(args.output.suffix + ".partial.jsonl")
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text("", encoding="utf-8")

    review_path = args.output.with_suffix(args.output.suffix + ".review.md")
    review_path.write_text(
        f"# Eval review — `{args.dataset.name}` -> `{args.output.name}`\n\n"
        f"Aggregate written at end.\n\n",
        encoding="utf-8",
    )

    def progress(i, total, case_result):
        marker = "." if (case_result.retrieval_hit is True or case_result.type == "negative") else "x"
        print(
            f"  [{i:>3}/{total}] {case_result.id:<8} {marker} "
            f"{case_result.latency_s:5.2f}s  {case_result.question[:70]}",
            flush=True,
        )
        with checkpoint_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(case_result), ensure_ascii=False) + "\n")
        with review_path.open("a", encoding="utf-8") as fh:
            sources_block = _render_sources_block(
                case_result.retrieved_source_ids,
                case_result.retrieved_previews,
                sources_by_id,
            )
            fh.write(
                f"\n## [{i}/{total}] {case_result.id} — {case_result.type} {marker}\n\n"
                f"- judge_score={case_result.judge_score}, grounded={case_result.judge_grounded}, "
                f"retrieval_hit={case_result.retrieval_hit}, latency={case_result.latency_s:.1f}s\n\n"
                f"Q: {case_result.question}\n\n"
                f"Gold: {case_result.gold_answer or '(none — expected refusal)'}\n\n"
                f"Model answer:\n\n{case_result.model_answer.strip()}\n\n"
                + (f"Judge rationale: {case_result.judge_rationale}\n\n" if case_result.judge_rationale else "")
                + f"{sources_block}\n\n"
                "---\n"
            )

    report = evaluate(
        engine,
        cases=cases,
        top_k=args.top_k,
        judge=None if args.no_judge else build_judge(),
        no_judge=args.no_judge,
        enable_ragas=args.ragas,
        repeats=args.repeat,
        on_progress=progress,
    )

    print("\n" + format_table(report["aggregate"]))
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    try:
        display_path = args.output.resolve().relative_to(ROOT)
    except ValueError:
        display_path = args.output
    print(f"\nwrote {display_path}")


if __name__ == "__main__":
    main()
