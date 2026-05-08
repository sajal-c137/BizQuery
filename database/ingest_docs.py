"""Bulk-ingest PDF (and other) files from data_sources/documents/ into ChromaDB.

Run from backend/:
    ../.venv/Scripts/python ../database/ingest_docs.py
Or from the project root:
    backend/.venv/Scripts/python database/ingest_docs.py
"""
import asyncio
import sys
import uuid
from pathlib import Path

# Resolve backend/ so imports work regardless of cwd
BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

DOCS_DIR = Path(__file__).parent / "data_sources" / "documents"
SUPPORTED = {".pdf", ".txt", ".md"}


async def main():
    from database import SessionLocal, init_db
    from models import Document
    from services.rag.pipeline import ingest_file

    init_db()
    db = SessionLocal()

    files = [f for f in sorted(DOCS_DIR.iterdir()) if f.suffix.lower() in SUPPORTED]
    if not files:
        print(f"No supported files found in {DOCS_DIR}")
        return

    for file_path in files:
        existing = db.query(Document).filter(Document.filename == file_path.name).first()
        if existing:
            print(f"  SKIP  {file_path.name}  (already ingested as {existing.doc_id})")
            continue

        doc_id = str(uuid.uuid4())
        suffix = file_path.suffix.lower().lstrip(".")
        doc = Document(doc_id=doc_id, filename=file_path.name, file_type=suffix, status="pending")
        db.add(doc)
        db.commit()

        try:
            chunk_count = await ingest_file(file_path, doc_id, file_path.name)
            doc.chunk_count = chunk_count
            doc.status = "ingested"
            db.commit()
            print(f"  OK    {file_path.name}  ({chunk_count} chunks)")
        except Exception as exc:
            doc.status = "failed"
            db.commit()
            print(f"  FAIL  {file_path.name}  {exc}")

    db.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
