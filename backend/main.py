import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import SessionLocal, init_db
from logger import get_logger
from routers import analytics, chat, documents

log = get_logger("main")

# folder with the bundled demo PDFs we auto-ingest on first boot
_SEED_DOCS_DIR = Path(__file__).parent.parent / "database" / "data_sources" / "documents"
_SEED_SUPPORTED = {".pdf", ".txt", ".md"}


async def _seed_demo_documents() -> None:
    # idempotent — reruns safely. Skips already-ingested files.
    if not _SEED_DOCS_DIR.exists():
        log.info("seed dir missing, skipping demo doc ingest: %s", _SEED_DOCS_DIR)
        return

    # imports inside the function so chroma init is lazy
    from models import Document
    from services.rag.pipeline import ingest_file

    files = [
        f for f in sorted(_SEED_DOCS_DIR.iterdir())
        if f.suffix.lower() in _SEED_SUPPORTED
    ]
    if not files:
        log.info("no demo docs found in %s", _SEED_DOCS_DIR)
        return

    log.info("seeding %d demo documents", len(files))
    db = SessionLocal()
    try:
        for f in files:
            try:
                # already ingested? leave it alone
                existing = db.query(Document).filter(Document.filename == f.name).first()
                if existing and existing.status == "ingested":
                    continue
                # half-ingested earlier — wipe and retry
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
                    log.info("seeded %s (%d chunks)", f.name, doc.chunk_count)
                except Exception:
                    # one bad file shouldn't kill startup
                    doc.status = "failed"
                    log.exception("failed to ingest seed doc: %s", f.name)
                db.commit()
            except Exception:
                log.exception("seed loop hiccup on %s — moving on", f.name)
                db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    log.info("backend starting up")
    init_db()
    try:
        await _seed_demo_documents()
    except Exception:
        # never block startup on seeding
        log.exception("demo seeding crashed; continuing without it")
    log.info("backend ready")
    yield
    # shutdown
    log.info("backend shutting down")


app = FastAPI(title="BizQuery API", version="1.0.0", lifespan=lifespan)

# CORS — origins come from env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# catch-all for unhandled errors so we never leak stack traces to the client
@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# wire up the routers
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(documents.router)


@app.get("/health")
def health():
    # cheap probe — used by docker healthchecks / load balancers
    return {"status": "ok"}
