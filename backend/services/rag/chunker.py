def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks, preferring natural break points."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        # Walk back to the nearest natural boundary
        for sep in ["\n\n", "\n", ". ", " "]:
            pos = text.rfind(sep, start, end)
            if pos > start + overlap:
                end = pos + len(sep)
                break
        chunks.append(text[start:end])
        start = end - overlap

    return [c.strip() for c in chunks if c.strip()]
