import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from logger import get_logger
from models import Document
from schemas import DocumentOut
from services.rag.pipeline import ingest_file, remove_document

log = get_logger("documents")
router = APIRouter(prefix="/documents", tags=["documents"])

# extensions we'll accept on upload
_SUPPORTED = {".pdf", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg", ".gif", ".webp"}

# safety cap so an attacker can't OOM the box with a huge upload
_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/ingest", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    file: UploadFile = File(...),
    sensitivity: str = Form("public"),
    db: Session = Depends(get_db),
):
    # validate extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _SUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}",
        )

    # validate sensitivity flag
    if sensitivity not in ("public", "internal"):
        raise HTTPException(
            status_code=400,
            detail="sensitivity must be 'public' or 'internal'",
        )

    # ensure upload dir exists (docker volume mount)
    upload_dir = Path(settings.upload_dir)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        log.exception("could not create upload dir %s", upload_dir)
        raise HTTPException(status_code=500, detail="Server upload dir unavailable")

    # read file bytes; reject if too big
    try:
        content = await file.read()
    except Exception:
        log.exception("failed to read upload stream")
        raise HTTPException(status_code=400, detail="Could not read uploaded file")
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {_MAX_BYTES // (1024 * 1024)} MB)",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # persist to disk under a generated id
    doc_id = str(uuid.uuid4())
    dest = upload_dir / f"{doc_id}{suffix}"
    try:
        dest.write_bytes(content)
    except OSError:
        log.exception("could not write upload to %s", dest)
        raise HTTPException(status_code=500, detail="Could not save upload")

    # create the DB row in 'pending' state
    doc = Document(
        doc_id=doc_id,
        filename=file.filename,
        file_type=suffix.lstrip("."),
        status="pending",
        sensitivity=sensitivity,
    )
    db.add(doc)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        log.exception("failed to create document row")
        # clean up the file we just wrote
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not register document")

    # try to ingest — failure marks the doc 'failed' but we don't lose the row
    try:
        doc.chunk_count = await ingest_file(dest, doc_id, file.filename)
        doc.status = "ingested"
        log.info("ingested %s (%d chunks)", file.filename, doc.chunk_count)
    except ValueError as exc:
        # extraction problem (bad PDF, image we can't describe, ...) — 4xx
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # unexpected backend issue — 5xx
        log.exception("unexpected ingest failure for %s", file.filename)
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    # mark success and return
    try:
        db.commit()
        db.refresh(doc)
    except SQLAlchemyError:
        db.rollback()
        log.exception("failed to mark doc ingested")
        raise HTTPException(status_code=500, detail="Could not finalize document")
    return doc


@router.get("/", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    # newest first
    try:
        return db.query(Document).order_by(Document.created_at.desc()).all()
    except SQLAlchemyError:
        log.exception("failed to list documents")
        raise HTTPException(status_code=500, detail="Could not list documents")


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    # find -> drop vectors -> drop row
    doc = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # vector delete is best-effort; vector_store logs and swallows on its own
    remove_document(doc_id)

    try:
        db.delete(doc)
        db.commit()
        log.info("deleted document %s", doc_id)
    except SQLAlchemyError:
        db.rollback()
        log.exception("failed to delete document row %s", doc_id)
        raise HTTPException(status_code=500, detail="Could not delete document")
