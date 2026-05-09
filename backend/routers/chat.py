from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Conversation, Document, Message
from schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationOut,
    MessageOut,
    SourceCitation,
)
from services.ai import get_ai_response
from services.data_proxy import get_data_context
from services.rag.pipeline import filter_by_access, retrieve_context
from services.source_router import route_sources

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_conversation(conv_id: int, db: Session) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    return db.query(Conversation).order_by(Conversation.created_at.desc()).all()


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: int, db: Session = Depends(get_db)):
    return _get_conversation(conv_id, db)


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
    conv = _get_conversation(conv_id, db)
    db.delete(conv)
    db.commit()


@router.post("/message", response_model=ChatResponse)
async def send_message(body: ChatRequest, db: Session = Depends(get_db)):
    if body.conversation_id:
        conv = _get_conversation(body.conversation_id, db)
    else:
        conv = Conversation(title=body.message[:60])
        db.add(conv)
        db.flush()

    user_msg = Message(conversation_id=conv.id, role="user", content=body.message)
    db.add(user_msg)
    db.flush()

    history = [{"role": m.role, "content": m.content} for m in conv.messages if m.id != user_msg.id]
    history.append({"role": "user", "content": body.message})

    data_contexts: list[dict] = []
    if body.source_ids:
        for sid in body.source_ids:
            try:
                data_contexts.append(get_data_context(sid, admin=body.admin))
            except FileNotFoundError:
                continue
    elif body.source_id == "auto":
        for sid in await route_sources(body.message):
            try:
                data_contexts.append(get_data_context(sid, admin=body.admin))
            except FileNotFoundError:
                continue
    elif body.source_id:
        try:
            data_contexts.append(get_data_context(body.source_id, admin=body.admin))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Data source '{body.source_id}' not found")

    rag_context = await retrieve_context(body.message)
    if rag_context and not body.admin:
        confidential = {
            d.doc_id for d in db.query(Document.doc_id).filter(Document.sensitivity == "internal").all()
        }
        rag_context = filter_by_access(rag_context, confidential)

    reply_text = await get_ai_response(
        history,
        data_contexts=data_contexts or None,
        rag_context=rag_context or None,
    )

    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=reply_text)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    cited_docs: list[str] = []
    seen: set[str] = set()
    for chunk in rag_context or []:
        name = chunk.get("metadata", {}).get("filename")
        if name and name not in seen:
            seen.add(name)
            cited_docs.append(name)

    message_out = MessageOut.model_validate(assistant_msg)
    message_out.sources = SourceCitation(
        csvs=[ctx["source_id"] for ctx in data_contexts],
        documents=cited_docs,
    )
    return {"conversation_id": conv.id, "message": message_out}
