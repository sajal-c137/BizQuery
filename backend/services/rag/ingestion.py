import base64
from pathlib import Path

from config import settings
from services.openai_client import client

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


async def extract_text(file_path: Path) -> str:
    """Dispatch to the correct extractor based on file extension."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix == ".csv":
        return _extract_csv(file_path)
    if suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="replace")
    if suffix in _MEDIA_TYPES:
        return await _describe_image(file_path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_csv(path: Path) -> str:
    import pandas as pd

    df = pd.read_csv(path)
    lines = [f"Columns: {', '.join(df.columns)}"]
    for _, row in df.iterrows():
        lines.append(", ".join(f"{k}={v}" for k, v in row.items()))
    return "\n".join(lines)


async def _describe_image(path: Path) -> str:
    media_type = _MEDIA_TYPES[path.suffix.lower()]
    data = base64.b64encode(path.read_bytes()).decode()
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
    return response.choices[0].message.content
