import re
from pathlib import Path

from logger import get_logger
from services.rag import vector_store as vs
from services.rag.chunker import chunk_text
from services.rag.embedder import embed_texts
from services.rag.ingestion import extract_text

log = get_logger("rag")

# minimal PII scrub at ingest time so PII never reaches the vector store,
# the LLM, or chat history. Regex-only — fast, no extra deps.
_PII_PATTERNS = [
    # email
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED-EMAIL]"),
    # phone (US-ish; tolerant of dashes/spaces/parens)
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED-PHONE]"),
    # SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
]


def _scrub_pii(text: str) -> str:
    # apply each PII pattern in turn
    for pattern, placeholder in _PII_PATTERNS:
        text = pattern.sub(placeholder, text)
    return text


def filter_by_access(chunks: list[dict], confidential_doc_ids: set[str]) -> list[dict]:
    # drop chunks belonging to confidential docs (used in non-admin mode)
    if not confidential_doc_ids:
        return chunks
    return [c for c in chunks if c["metadata"].get("doc_id") not in confidential_doc_ids]


async def ingest_file(file_path: Path, doc_id: str, filename: str) -> int:
    # full ingest: extract -> chunk -> scrub -> embed -> store
    log.info("ingest start: %s (doc_id=%s)", filename, doc_id)

    # 1. extract raw text
    text = await extract_text(file_path)

    # 2. chunk and scrub PII before anything touches the vector store
    chunks = [_scrub_pii(c) for c in chunk_text(text)]
    if not chunks:
        log.warning("ingest produced 0 chunks for %s", filename)
        return 0

    # 3. embed
    embeddings = await embed_texts(chunks)

    # 4. metadata for retrieval (filename for citations, index for ordering)
    metadata = [
        {"doc_id": doc_id, "filename": filename, "chunk_index": i}
        for i in range(len(chunks))
    ]

    # 5. persist
    vs.upsert_chunks(doc_id, chunks, embeddings, metadata)

    log.info("ingest done: %s -> %d chunks", filename, len(chunks))
    return len(chunks)


async def retrieve_context(query: str, n_results: int = 5) -> list[dict]:
    # embed the query, hit the vector store, return top chunks
    if not query.strip():
        return []
    try:
        [query_embedding] = await embed_texts([query])
    except Exception:
        # already logged in embedder — RAG is best-effort
        log.warning("query embedding failed; skipping retrieval")
        return []
    return vs.query_chunks(query_embedding, n_results)


def remove_document(doc_id: str) -> None:
    # mirror the ingest API: simple, idempotent
    vs.delete_document(doc_id)
