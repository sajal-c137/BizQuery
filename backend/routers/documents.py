import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Document
from schemas import DocumentOut
from services.rag.pipeline import ingest_file, remove_document

router = APIRouter(prefix="/documents", tags=["documents"])

_SUPPORTED = {".pdf", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg", ".gif", ".webp"}


@router.post("/ingest", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def ingest_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    doc_id = str(uuid.uuid4())
    dest = upload_dir / f"{doc_id}{suffix}"
    dest.write_bytes(await file.read())

    doc = Document(doc_id=doc_id, filename=file.filename, file_type=suffix.lstrip("."), status="pending")
    db.add(doc)
    db.commit()

    try:
        doc.chunk_count = await ingest_file(dest, doc_id, file.filename)
        doc.status = "ingested"
    except Exception as exc:
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    db.commit()
    db.refresh(doc)
    return doc


@router.get("/", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    remove_document(doc_id)
    db.delete(doc)
    db.commit()
