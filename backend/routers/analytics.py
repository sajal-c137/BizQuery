from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from logger import get_logger
from schemas import AnalyticsRequest, AnalyticsResponse
from services.ai import get_ai_response
from services.charts import get_chart_bundle
from services.context import get_filtered_rag, resolve_data_contexts
from services.data_proxy import list_sources

log = get_logger("analytics")
router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sources")
def get_sources() -> list[dict]:
    # list all available CSV data sources
    try:
        return list_sources()
    except Exception:
        log.exception("failed to list sources")
        raise HTTPException(status_code=500, detail="Could not list sources")


@router.get("/charts/{source_id}")
def get_charts(source_id: str, admin: bool = False) -> dict:
    # chart-friendly summaries for the visualization panel
    try:
        return get_chart_bundle(source_id, admin=admin)
    except FileNotFoundError as e:
        # 404: bad source id
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # 400: source exists but failed to parse
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        log.exception("chart bundle failed for %s", source_id)
        raise HTTPException(status_code=500, detail="Could not build charts")


@router.post("/query", response_model=AnalyticsResponse)
async def analytics_query(body: AnalyticsRequest, db: Session = Depends(get_db)) -> AnalyticsResponse:
    # quick guard against empty inputs
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # resolve CSV data contexts (may be auto-routed)
    try:
        data_contexts = await resolve_data_contexts(
            body.source_id, None, body.admin, body.question
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # add document RAG context with access policy applied
    rag_context = await get_filtered_rag(body.question, db, body.admin)

    log.info(
        "analytics sources=%d rag_chunks=%d admin=%s",
        len(data_contexts), len(rag_context), body.admin,
    )

    answer = await get_ai_response(
        [{"role": "user", "content": body.question}],
        data_contexts=data_contexts or None,
        rag_context=rag_context or None,
    )

    # which source(s) we actually used (or fall back to the requested id)
    selected = ",".join(c["source_id"] for c in data_contexts) or body.source_id
    return AnalyticsResponse(answer=answer, source_id=selected)
