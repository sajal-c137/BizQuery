from datetime import datetime

from pydantic import BaseModel


class SourceCitation(BaseModel):
    csvs: list[str] = []
    documents: list[str] = []


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    sources: SourceCitation | None = None

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str
    source_id: str | None = None
    source_ids: list[str] | None = None
    admin: bool = False


class ChatResponse(BaseModel):
    conversation_id: int
    message: MessageOut


class DocumentOut(BaseModel):
    id: int
    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    status: str
    sensitivity: str = "public"
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsRequest(BaseModel):
    question: str
    source_id: str | None = None
    admin: bool = False


class AnalyticsResponse(BaseModel):
    answer: str
    source_id: str | None = None
