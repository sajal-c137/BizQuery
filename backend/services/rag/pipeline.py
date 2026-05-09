import re
from pathlib import Path

from services.rag import vector_store as vs
from services.rag.chunker import chunk_text
from services.rag.embedder import embed_texts
from services.rag.ingestion import extract_text

# Minimal PII scrub applied at ingest time so PII never reaches the vector
# store, the LLM, or chat history. Regex-only — fast, no extra dependencies.
_PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED-EMAIL]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED-PHONE]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
]


def _scrub_pii(text: str) -> str:
    for pattern, placeholder in _PII_PATTERNS:
        text = pattern.sub(placeholder, text)
    return text


def filter_by_access(chunks: list[dict], confidential_doc_ids: set[str]) -> list[dict]:
    """Drop chunks whose source document is flagged confidential."""
    if not confidential_doc_ids:
        return chunks
    return [c for c in chunks if c["metadata"].get("doc_id") not in confidential_doc_ids]


async def ingest_file(file_path: Path, doc_id: str, filename: str) -> int:
    """Extract, chunk, embed, and store a document. Returns number of chunks stored."""
    text = await extract_text(file_path)
    chunks = [_scrub_pii(c) for c in chunk_text(text)]
    if not chunks:
        return 0
    embeddings = await embed_texts(chunks)
    metadata = [{"doc_id": doc_id, "filename": filename, "chunk_index": i} for i in range(len(chunks))]
    vs.upsert_chunks(doc_id, chunks, embeddings, metadata)
    return len(chunks)


async def retrieve_context(query: str, n_results: int = 5) -> list[dict]:
    """Embed a query and return the top-k most relevant chunks."""
    [query_embedding] = await embed_texts([query])
    return vs.query_chunks(query_embedding, n_results)


def remove_document(doc_id: str) -> None:
    vs.delete_document(doc_id)
