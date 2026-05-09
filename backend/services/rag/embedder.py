import asyncio

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from logger import get_logger

log = get_logger("embedder")

# all-MiniLM-L6-v2 ONNX — downloaded once to ~/.cache/chroma on first use
# baked into the docker image at build time so the container has no egress
_ef = DefaultEmbeddingFunction()
EMBEDDING_DIM = 384


async def embed_texts(texts: list[str]) -> list[list[float]]:
    # batch embed a list of strings
    if not texts:
        return []
    try:
        # ONNX is sync; push it off the event loop
        embeddings = await asyncio.to_thread(_ef, texts)
        return [e.tolist() for e in embeddings]
    except Exception:
        # bubble up — callers decide what fallback (if any) to use
        log.exception("embedding failed for %d texts", len(texts))
        raise
