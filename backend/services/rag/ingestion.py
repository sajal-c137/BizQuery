import base64
from pathlib import Path

from config import settings
from logger import get_logger
from services.openai_client import client

log = get_logger("ingest")

# image extensions we send to the LLM for description
_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


async def extract_text(file_path: Path) -> str:
    # dispatch to the right extractor based on extension
    suffix = file_path.suffix.lower()
    log.info("extracting text from %s (%s)", file_path.name, suffix)

    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix == ".csv":
        return _extract_csv(file_path)
    if suffix in (".txt", ".md"):
        # tolerant decoding so weird encodings don't kill ingest
        return file_path.read_text(encoding="utf-8", errors="replace")
    if suffix in _MEDIA_TYPES:
        return await _describe_image(file_path)

    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(path: Path) -> str:
    # lazy import — pypdf is optional unless someone uploads a PDF
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
    except Exception:
        log.exception("failed to open PDF: %s", path)
        raise ValueError("Could not open PDF (file may be corrupt or encrypted)")

    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            # one bad page shouldn't tank the whole doc
            log.warning("page %d of %s failed to extract", i, path.name)
            pages.append("")
    return "\n\n".join(pages)


def _extract_csv(path: Path) -> str:
    # lazy import for CSV path too
    import pandas as pd

    try:
        df = pd.read_csv(path)
    except Exception:
        log.exception("failed to read CSV: %s", path)
        raise ValueError("Could not parse CSV file")

    lines = [f"Columns: {', '.join(df.columns)}"]
    for _, row in df.iterrows():
        lines.append(", ".join(f"{k}={v}" for k, v in row.items()))
    return "\n".join(lines)


async def _describe_image(path: Path) -> str:
    # ask the LLM to describe the image, then index the description
    media_type = _MEDIA_TYPES[path.suffix.lower()]
    try:
        data = base64.b64encode(path.read_bytes()).decode()
    except OSError:
        log.exception("could not read image bytes: %s", path)
        raise ValueError("Could not read image file")

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{data}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Describe this image in full detail, including all visible text, "
                            "data, charts, tables, and any relevant information. "
                            "This description will be indexed for semantic search."
                        ),
                    },
                ],
            }],
            max_tokens=1000,
        )
    except Exception:
        log.exception("image description failed for %s", path.name)
        raise ValueError("Image description failed — model unreachable or rejected the request")

    content = response.choices[0].message.content if response.choices else None
    return content or ""
