from pathlib import Path

from services.rag import vector_store as vs
from services.rag.chunker import chunk_text
from services.rag.embedder import embed_texts
from services.rag.ingestion import extract_text


async def ingest_file(file_path: Path, doc_id: str, filename: str) -> int:
    """Extract, chunk, embed, and store a document. Returns number of chunks stored."""
    text = await extract_text(file_path)
    chunks = chunk_text(text)
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
