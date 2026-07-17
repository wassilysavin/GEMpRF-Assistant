import argparse
import json
import os

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

from transformers.utils import logging as _hf_logging

_hf_logging.disable_progress_bar()

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from . import tracing  # noqa: E402  (env setup above must precede package imports)
from .evaluation import evaluate, format_table, load_eval_set  # noqa: E402
from .pipeline.engine import GraphRagEngine  # noqa: E402

_SOURCE_TYPE_TAG = {
    "paper": "paper",
    "website": "docs",
    "repo": "code",
    "code": "code",
    "github": "code",
    "demokit": "DemoKit",
}


def _source_kind(source_id: str) -> str:
    return _SOURCE_TYPE_TAG.get(source_id.split(".", 1)[0], "source")


def _print_citations(citations) -> None:
    if not citations:
        return
    print("\nSources used:")
    seen: set[str] = set()
    for citation in citations:
        if citation.id in seen:
            continue
        seen.add(citation.id)
        heading = " > ".join(citation.heading_path) if citation.heading_path else ""
        title = citation.title or citation.id
        tag = _source_kind(citation.id)
        line = f"  - {title} ({tag})"
        if heading and heading.lower() != title.lower():
            line += f" — {heading}"
        print(line)


def _print_analysis_result(analysis) -> None:
    """Print a QueryAnalysis (answer + matched params + sources)."""
    print(analysis.answer)
    if analysis.matched_parameter_labels:
        print("\nMatched parameters:")
        for label in analysis.matched_parameter_labels:
            print(f"  - {label}")
    _print_citations(analysis.citations)


def _answer_question(engine, question: str, history=None):
    """Answer one question; the clarifier asks follow-ups when it can't ground it, and stops on its own if no reply is available (EOF)."""
    analysis = engine.answer(question, history=history, clarify=True)
    _print_analysis_result(analysis)
    return analysis


def _print_trace_url(engine) -> None:
    """Point at the Langfuse trace for the answer just printed (silent when tracing is off)."""
    url = getattr(engine, "last_trace_url", None)
    if url:
        print(f"\nTrace: {url}")


def _print_analysis(analysis) -> None:
    print(f"Status: {analysis.status}")
    print(f"Reranked: {analysis.rerank_used}")
    print(f"\n{analysis.answer}")
    if analysis.matched_parameter_labels:
        print("\nMatched parameters:")
        for label, pid in zip(analysis.matched_parameter_labels, analysis.matched_parameter_ids):
            print(f"- {label} [{pid}]")
    if analysis.evidence:
        print("\nEvidence:")
        for item in analysis.evidence:
            heading = " > ".join(item.heading_path) if item.heading_path else "(top)"
            preview = item.text[:160].replace("\n", " ")
            print(f"- [{item.source_id}] {heading} (score={item.score:.3f})\n  {preview}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GEM-pRF Graph-RAG CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser(
        "ask", help="Ask a question (asks follow-ups if it can't answer and you're at a terminal)"
    )
    ask_parser.add_argument("question")
    ask_parser.add_argument("--json", action="store_true")
    ask_parser.add_argument("--top-k", type=int, default=6)

    debug_parser = subparsers.add_parser("debug", help="Show retrieval + grounding for one question")
    debug_parser.add_argument("question")
    debug_parser.add_argument("--json", action="store_true")
    debug_parser.add_argument("--top-k", type=int, default=6)

    subparsers.add_parser("repl", help="Run an interactive console")
    subparsers.add_parser("describe", help="Print engine metadata")

    eval_parser = subparsers.add_parser("eval", help="Run the 100-question paper eval")
    eval_parser.add_argument("--top-k", type=int, default=6)
    eval_parser.add_argument("--limit", type=int, default=None)
    eval_parser.add_argument("--no-judge", action="store_true")
    eval_parser.add_argument("--json", action="store_true")

    index_parser = subparsers.add_parser("index", help="Build or rebuild the local index from the corpus")
    index_sub = index_parser.add_subparsers(dest="index_command", required=True)
    build_parser = index_sub.add_parser("build", help="Chunk + embed the corpus into Weaviate and rebuild kg.ttl")
    build_parser.add_argument("--force", action="store_true", help="Rebuild even when an index already exists")

    snapshot_parser = subparsers.add_parser("snapshot", help="Pack or install a prebuilt index snapshot")
    snapshot_sub = snapshot_parser.add_subparsers(dest="snapshot_command", required=True)
    pack_parser = snapshot_sub.add_parser("pack", help="Archive the current index (stop any running assistant first)")
    pack_parser.add_argument("--out", default=None, help="Archive path (default: ./gemprf-index-snapshot.tar.gz)")
    install_parser = snapshot_sub.add_parser("install", help="Install a snapshot (local path or URL) into the data dir")
    install_parser.add_argument("source")
    install_parser.add_argument("--force", action="store_true", help="Replace an existing index")

    args = parser.parse_args()

    if args.command == "index":
        engine = GraphRagEngine(auto_ingest=False, reranker=False, llm=False)
        try:
            if engine._is_populated() and not args.force:
                raise SystemExit("Index already exists; pass --force to rebuild it from the corpus.")
            print(json.dumps(engine.ingest(), indent=2))
        finally:
            engine.close()
        return

    # Snapshot commands must run without booting the engine (no index may exist yet).
    if args.command == "snapshot":
        from .kb.snapshot import install, pack
        from .paths import data_dir

        if args.snapshot_command == "pack":
            print(f"Wrote {pack(args.out)}")
        else:
            manifest = install(args.source, force=args.force)
            print(f"Installed snapshot into {data_dir()}")
            backend = manifest.get("embedding_backend", "unknown")
            print(f"Index was built with embedding backend: {backend} — configure the same one for queries.")
        return

    if args.command in {"ask", "repl"}:
        from .preflight import check_local_llm

        check_local_llm()

    engine = GraphRagEngine()

    try:
        if args.command == "ask":
            if args.json:
                print(json.dumps(engine.ask_dict(args.question, top_k=args.top_k), indent=2))
            else:
                _answer_question(engine, args.question)
                _print_trace_url(engine)
            return

        if args.command == "debug":
            analysis = engine.analyze(args.question, top_k=args.top_k)
            if args.json:
                payload = engine.ask_dict(args.question, top_k=args.top_k)
                print(json.dumps(payload, indent=2))
            else:
                _print_analysis(analysis)
                _print_trace_url(engine)
            return

        if args.command == "describe":
            print(json.dumps(engine.describe(), indent=2))
            return

        if args.command == "eval":
            cases = load_eval_set()
            if args.limit:
                cases = cases[: args.limit]
            report = evaluate(engine, cases=cases, top_k=args.top_k, no_judge=args.no_judge)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(format_table(report["aggregate"]))
            return

        # repl: keep a rolling conversation history so follow-ups resolve across turns
        from .conversation import ConversationHistory, history_enabled

        history = ConversationHistory() if history_enabled() else None
        while True:
            try:
                question = input("gemprf> ").strip()
            except EOFError:
                print()
                break
            if not question or question.lower() in {"exit", "quit"}:
                break
            analysis = _answer_question(engine, question, history)
            _print_trace_url(engine)
            if history is not None:
                # Record the raw user turn (not the resolved/reformulated query, which would feed
                # stale context back into history); the answer already carries the substance.
                history.add(question, analysis.answer)
            print()
    finally:
        tracing.flush()
        engine.close()


def ask_main() -> None:
    parser = argparse.ArgumentParser(
        prog="gemprf-ask",
        description="Ask GEM-pRF a question",
    )
    parser.add_argument("question", help="A question about GEM-pRF.")
    parser.add_argument("--top-k", type=int, default=6, help="Chunks to retrieve (default 6).")
    parser.add_argument("--json", action="store_true", help="Print the full response as JSON.")
    args = parser.parse_args()

    from .preflight import check_local_llm

    check_local_llm()

    engine = GraphRagEngine()
    try:
        if args.json:
            print(json.dumps(engine.ask_dict(args.question, top_k=args.top_k), indent=2))
        else:
            _answer_question(engine, args.question)
            _print_trace_url(engine)
    finally:
        tracing.flush()
        engine.close()


if __name__ == "__main__":
    main()
