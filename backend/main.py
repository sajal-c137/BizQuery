import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import SessionLocal, init_db
from routers import analytics, chat, documents

_SEED_DOCS_DIR = Path(__file__).parent.parent / "database" / "data_sources" / "documents"
_SEED_SUPPORTED = {".pdf", ".txt", ".md"}


async def _seed_demo_documents() -> None:
    """Idempotent bulk-ingest of demo PDFs so the chat works out of the box."""
    if not _SEED_DOCS_DIR.exists():
        return

    from models import Document
    from services.rag.pipeline import ingest_file

    files = [f for f in sorted(_SEED_DOCS_DIR.iterdir()) if f.suffix.lower() in _SEED_SUPPORTED]
    if not files:
        return

    db = SessionLocal()
    try:
        for f in files:
            existing = db.query(Document).filter(Document.filename == f.name).first()
            if existing and existing.status == "ingested":
                continue
            if existing:
                db.delete(existing)
                db.commit()

            doc = Document(
                doc_id=str(uuid.uuid4()),
                filename=f.name,
                file_type=f.suffix.lower().lstrip("."),
                status="pending",
            )
            db.add(doc)
            db.commit()
            try:
                doc.chunk_count = await ingest_file(f, doc.doc_id, f.name)
                doc.status = "ingested"
            except Exception:
                doc.status = "failed"
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await _seed_demo_documents()
    yield


app = FastAPI(title="BizQuery API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(documents.router)


@app.get("/health")
def health():
    return {"status": "ok"}
