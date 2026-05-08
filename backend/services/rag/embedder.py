import asyncio

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# all-MiniLM-L6-v2 ONNX model — downloaded once to ~/.cache/chroma on first use
_ef = DefaultEmbeddingFunction()
EMBEDDING_DIM = 384


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    # Run synchronous ONNX inference in a thread so it doesn't block the event loop
    embeddings = await asyncio.to_thread(_ef, texts)
    return [list(e) for e in embeddings]
