from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from logger import get_logger

log = get_logger("vectors")

_COLLECTION = "documents"


def _collection():
    # build (or reopen) the persistent chroma collection
    path = Path(settings.chroma_dir)
    path.mkdir(parents=True, exist_ok=True)
    c = chromadb.PersistentClient(
        path=str(path),
        # disable telemetry — runs offline in docker
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    # cosine distance is more forgiving than L2 for sentence embeddings
    return c.get_or_create_collection(name=_COLLECTION, metadata={"hnsw:space": "cosine"})


def upsert_chunks(
    doc_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: list[dict],
) -> None:
    # write (or replace) every chunk for this doc
    if not chunks:
        return
    ids = [f"{doc_id}__chunk_{i}" for i in range(len(chunks))]
    try:
        _collection().upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadata,
        )
        log.info("upserted %d chunks for doc %s", len(chunks), doc_id)
    except Exception:
        log.exception("vector upsert failed for doc %s", doc_id)
        raise


def query_chunks(
    query_embedding: list[float],
    n_results: int = 5,
    min_score: float = 0.35,
) -> list[dict]:
    # similarity search — returns top chunks above the similarity floor
    try:
        col = _collection()
        count = col.count()
    except Exception:
        log.exception("could not open chroma collection")
        return []

    # empty store — nothing to retrieve
    if count == 0:
        return []

    try:
        results = col.query(
            query_embeddings=[query_embedding],
            # don't ask for more than exists
            n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        log.exception("chroma query failed")
        return []

    # convert to chunk dicts; chroma distance is cosine -> similarity = 1 - dist
    chunks = [
        {"text": text, "metadata": meta, "score": round(1 - dist, 4)}
        for text, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]
    # filter weak matches
    return [c for c in chunks if c["score"] >= min_score]


def delete_document(doc_id: str) -> None:
    # drop every chunk for this doc
    try:
        _collection().delete(where={"doc_id": doc_id})
        log.info("deleted chunks for doc %s", doc_id)
    except Exception:
        # don't blow up — caller might still want to drop the DB row
        log.exception("vector delete failed for doc %s", doc_id)
