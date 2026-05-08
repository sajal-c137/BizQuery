from pathlib import Path

import chromadb

from config import settings

_COLLECTION = "documents"


def _collection():
    path = Path(settings.chroma_dir)
    path.mkdir(parents=True, exist_ok=True)
    c = chromadb.PersistentClient(path=str(path))
    return c.get_or_create_collection(name=_COLLECTION, metadata={"hnsw:space": "cosine"})


def upsert_chunks(
    doc_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: list[dict],
) -> None:
    ids = [f"{doc_id}__chunk_{i}" for i in range(len(chunks))]
    _collection().upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadata)


def query_chunks(query_embedding: list[float], n_results: int = 5) -> list[dict]:
    col = _collection()
    count = col.count()
    if count == 0:
        return []
    results = col.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"text": text, "metadata": meta, "score": round(1 - dist, 4)}
        for text, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


def delete_document(doc_id: str) -> None:
    _collection().delete(where={"doc_id": doc_id})
