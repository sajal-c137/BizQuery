"""Shared helpers used by both /chat and /analytics routers."""
from sqlalchemy.orm import Session

from logger import get_logger
from models import Document
from services.data_proxy import get_data_context
from services.rag.pipeline import filter_by_access, retrieve_context
from services.source_router import route_sources

log = get_logger("context")


async def resolve_data_contexts(
    source_id: str | None,
    source_ids: list[str] | None,
    admin: bool,
    question: str,
) -> list[dict]:
    # turns the various source-picking modes into a list of data contexts.
    # missing sources are skipped (with a warning), never fatal —
    # except in the single-id case, where the caller wants a hard 404.
    contexts: list[dict] = []

    # 1. multi-source list (preferred path)
    if source_ids:
        for sid in source_ids:
            try:
                contexts.append(get_data_context(sid, admin=admin))
            except FileNotFoundError:
                log.warning("requested source not found: %s", sid)
            except Exception:
                log.exception("could not load source %s", sid)
        return contexts

    # 2. "auto" mode — let the LLM pick
    if source_id == "auto":
        for sid in await route_sources(question):
            try:
                contexts.append(get_data_context(sid, admin=admin))
            except FileNotFoundError:
                log.warning("router picked missing source: %s", sid)
            except Exception:
                log.exception("router-picked source failed: %s", sid)
        return contexts

    # 3. single id — re-raise FileNotFoundError so the router can 404
    if source_id:
        contexts.append(get_data_context(source_id, admin=admin))

    return contexts


async def get_filtered_rag(query: str, db: Session, admin: bool) -> list[dict]:
    # retrieve top chunks, then enforce confidential-doc access if not admin
    chunks = await retrieve_context(query)
    if not chunks or admin:
        return chunks

    try:
        confidential = {
            d.doc_id
            for d in db.query(Document.doc_id).filter(Document.sensitivity == "internal").all()
        }
    except Exception:
        # if the DB query fails, default to "drop everything" -> safe choice
        log.exception("could not fetch confidential doc list; dropping RAG context")
        return []

    return filter_by_access(chunks, confidential)
