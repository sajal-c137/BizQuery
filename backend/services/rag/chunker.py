def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    # split a doc into overlapping chunks, preferring natural boundaries
    text = text.strip()
    if not text:
        return []
    # tiny doc — one chunk
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # last chunk — take everything remaining
        if end >= len(text):
            chunks.append(text[start:])
            break
        # walk back to the nearest natural break
        # tries paragraph, line, sentence, then word
        for sep in ["\n\n", "\n", ". ", " "]:
            pos = text.rfind(sep, start, end)
            # only accept the break if it's not too close to the start
            if pos > start + overlap:
                end = pos + len(sep)
                break
        chunks.append(text[start:end])
        # slide forward, keeping `overlap` chars of context
        start = end - overlap

    # drop accidental empties
    return [c.strip() for c in chunks if c.strip()]
