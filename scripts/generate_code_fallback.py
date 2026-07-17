"""Regenerate the code-entity fallback artifact (corpus/code_entities.json) from the tool source."""
from gemprf_assistant.kb import code_index


def main() -> None:
    summary = code_index.write_artifact()
    print(f"wrote {code_index.ARTIFACT_PATH}")
    print(f"  entities: {summary['entities']}  by_kind: {summary['by_kind']}")
    if summary["skipped"]:
        print(f"  skipped (parse errors): {summary['skipped']}")


if __name__ == "__main__":
    main()
