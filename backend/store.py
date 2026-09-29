"""Local Chroma collection used as the RAG vector database."""

import hashlib
from pathlib import Path

import chromadb

BACKEND_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BACKEND_DIR / "chroma_data"
COLLECTION_NAME = "docs"
CHUNK_SIZE = 500


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            split = text.rfind(" ", start, end)
            if split > start + size // 2:
                end = split
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == start:
            end = start + 1
        start = end
    return chunks


class VectorStore:
    def __init__(self, path: Path = CHROMA_PATH) -> None:
        self._path = path
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            self._path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self._path))
            self._collection = self._client.get_or_create_collection(name=COLLECTION_NAME)
        return self._collection

    def count(self) -> int:
        return self._get_collection().count()

    def ingest(self, text: str, source: str) -> int:
        chunks = chunk_text(text)
        if not chunks:
            return 0
        collection = self._get_collection()
        existing = collection.get(where={"source": source})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
        ids = [
            hashlib.sha256(f"{source}:{index}:{chunk}".encode("utf-8")).hexdigest()
            for index, chunk in enumerate(chunks)
        ]
        collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=[{"source": source, "index": index} for index in range(len(chunks))],
        )
        return len(chunks)

    def query(self, text: str, n_results: int = 4) -> list[dict]:
        collection = self._get_collection()
        total = collection.count()
        if total == 0 or not text.strip():
            return []
        result = collection.query(query_texts=[text], n_results=min(n_results, total))
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        sources = []
        for index, document in enumerate(documents):
            meta = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
            sources.append(
                {
                    "id": ids[index],
                    "text": document,
                    "source": meta.get("source", "unknown"),
                    "distance": distances[index] if index < len(distances) else None,
                }
            )
        return sources


store = VectorStore()
