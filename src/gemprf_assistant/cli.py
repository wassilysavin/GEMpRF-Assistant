import argparse
import json

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


def _print_result(result) -> None:
    print(result.answer)
    if result.matched_parameters:
        print("\nMatched parameters:")
        for parameter in result.matched_parameters:
            print(f"  - {parameter}")
    if result.citations:
        print("\nSources used:")
        seen: set[str] = set()
        for citation in result.citations:
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

    ask_parser = subparsers.add_parser("ask", help="Ask one question")
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
    engine = GraphRagEngine()

    try:
        if args.command == "ask":
            if args.json:
                print(json.dumps(engine.ask_dict(args.question, top_k=args.top_k), indent=2))
            else:
                _print_result(engine.ask(args.question, top_k=args.top_k))
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

        # repl
        while True:
            try:
                question = input("gemprf> ").strip()
            except EOFError:
                print()
                break
            if not question or question.lower() in {"exit", "quit"}:
                break
            _print_result(engine.ask(question))
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

    engine = GraphRagEngine()
    try:
        if args.json:
            print(json.dumps(engine.ask_dict(args.question, top_k=args.top_k), indent=2))
        else:
            _print_result(engine.ask(args.question, top_k=args.top_k))
    finally:
        engine.close()


if __name__ == "__main__":
    main()
