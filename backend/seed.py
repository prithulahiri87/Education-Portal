"""Load the sample knowledge file into the local Chroma collection."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.store import store

SAMPLE = Path(__file__).resolve().parent / "knowledge" / "sample.md"


def main() -> None:
    text = SAMPLE.read_text(encoding="utf-8")
    chunks = store.ingest(text, SAMPLE.name)
    print(f"Ingested {chunks} chunks from {SAMPLE.name}. Collection size: {store.count()}")


if __name__ == "__main__":
    main()
