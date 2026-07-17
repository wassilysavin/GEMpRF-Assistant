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

from .evaluation import evaluate, format_table, load_eval_set
from .rag.engine import GraphRagEngine


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
    from .clarification import answer_with_clarification

    analysis = answer_with_clarification(engine, question, history=history)
    _print_analysis_result(analysis)
    return analysis


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

    args = parser.parse_args()

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
            return

        if args.command == "debug":
            analysis = engine.analyze(args.question, top_k=args.top_k)
            if args.json:
                payload = engine.ask_dict(args.question, top_k=args.top_k)
                print(json.dumps(payload, indent=2))
            else:
                _print_analysis(analysis)
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
            if history is not None:
                # Record the raw user turn (not the resolved/reformulated query, which would feed
                # stale context back into history); the answer already carries the substance.
                history.add(question, analysis.answer)
            print()
    finally:
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
    finally:
        engine.close()


if __name__ == "__main__":
    main()
