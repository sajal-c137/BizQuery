from fastapi import APIRouter, HTTPException

from schemas import AnalyticsRequest, AnalyticsResponse
from services.ai import get_ai_response
from services.data_proxy import get_data_context, list_sources
from services.rag.pipeline import retrieve_context
from services.source_router import route_sources

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sources")
def get_sources() -> list[dict]:
    """List all available CSV data sources."""
    return list_sources()


@router.post("/query", response_model=AnalyticsResponse)
async def analytics_query(body: AnalyticsRequest) -> AnalyticsResponse:
    data_contexts: list[dict] = []
    if body.source_id == "auto":
        for sid in await route_sources(body.question):
            try:
                data_contexts.append(get_data_context(sid, admin=body.admin))
            except FileNotFoundError:
                continue
    elif body.source_id:
        try:
            data_contexts.append(get_data_context(body.source_id, admin=body.admin))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Retrieve semantically relevant chunks from ingested documents
    rag_context = await retrieve_context(body.question)

    answer = await get_ai_response(
        [{"role": "user", "content": body.question}],
        data_contexts=data_contexts or None,
        rag_context=rag_context or None,
    )
    selected = ",".join(c["source_id"] for c in data_contexts) or body.source_id
    return AnalyticsResponse(answer=answer, source_id=selected)
