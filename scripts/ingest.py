import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from gemprf_assistant.rag.engine import GraphRagEngine  # noqa: E402  (dotenv load above)


def main() -> None:
    engine = GraphRagEngine(auto_ingest=False, reranker=False, llm=False)
    try:
        stats = engine.ingest()
    finally:
        engine.close()
    print(
        f"Ingested {stats['chunks']} chunks across {stats['sections']} sections, "
        f"{stats['parameters']} parameters, {stats['sources']} sources."
    )


if __name__ == "__main__":
    main()
