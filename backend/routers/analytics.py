from fastapi import APIRouter, HTTPException

from schemas import AnalyticsRequest, AnalyticsResponse
from services.ai import get_ai_response
from services.data_proxy import get_data_context, list_sources
from services.rag.pipeline import retrieve_context

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sources")
def get_sources() -> list[dict]:
    """List all available CSV data sources."""
    return list_sources()


@router.post("/query", response_model=AnalyticsResponse)
async def analytics_query(body: AnalyticsRequest) -> AnalyticsResponse:
    data_context = None
    if body.source_id:
        try:
            data_context = get_data_context(body.source_id)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Retrieve semantically relevant chunks from ingested documents
    rag_context = await retrieve_context(body.question)

    answer = await get_ai_response(
        [{"role": "user", "content": body.question}],
        data_context=data_context,
        rag_context=rag_context or None,
    )
    return AnalyticsResponse(answer=answer, source_id=body.source_id)
