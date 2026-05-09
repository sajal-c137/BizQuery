from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from logger import get_logger
from models import Conversation, Message
from schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationOut,
    MessageOut,
    SourceCitation,
)
from services.ai import get_ai_response
from services.context import get_filtered_rag, resolve_data_contexts

log = get_logger("chat")
router = APIRouter(prefix="/chat", tags=["chat"])


def _get_conversation(conv_id: int, db: Session) -> Conversation:
    # one place to load + 404 a conversation
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    # newest first
    try:
        return db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    except SQLAlchemyError:
        log.exception("failed to list conversations")
        raise HTTPException(status_code=500, detail="Could not list conversations")


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: int, db: Session = Depends(get_db)):
    return _get_conversation(conv_id, db)


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
    conv = _get_conversation(conv_id, db)
    try:
        db.delete(conv)
        db.commit()
        log.info("deleted conversation %d", conv_id)
    except SQLAlchemyError:
        db.rollback()
        log.exception("failed to delete conversation %d", conv_id)
        raise HTTPException(status_code=500, detail="Could not delete conversation")


@router.post("/message", response_model=ChatResponse)
async def send_message(body: ChatRequest, db: Session = Depends(get_db)):
    # guard: empty messages aren't useful and cost LLM tokens
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # fetch existing conv, or open a new one with the first message as title
    if body.conversation_id:
        conv = _get_conversation(body.conversation_id, db)
    else:
        conv = Conversation(title=body.message[:60])
        db.add(conv)
        try:
            db.flush()
        except SQLAlchemyError:
            db.rollback()
            log.exception("failed to create conversation")
            raise HTTPException(status_code=500, detail="Could not start conversation")

    # save the user's message right away — even if AI fails, we keep the trail
    user_msg = Message(conversation_id=conv.id, role="user", content=body.message)
    db.add(user_msg)
    try:
        db.flush()
    except SQLAlchemyError:
        db.rollback()
        log.exception("failed to persist user message")
        raise HTTPException(status_code=500, detail="Could not persist user message")

    # rebuild history from DB; tack on the new message at the end
    history = [
        {"role": m.role, "content": m.content}
        for m in conv.messages
        if m.id != user_msg.id
    ]
    history.append({"role": "user", "content": body.message})

    # collect data contexts (CSVs)
    try:
        data_contexts = await resolve_data_contexts(
            body.source_id, body.source_ids, body.admin, body.message
        )
    except FileNotFoundError:
        # only happens for the explicit single-id path
        raise HTTPException(
            status_code=404,
            detail=f"Data source '{body.source_id}' not found",
        )

    # collect RAG context (documents) with access policy applied
    rag_context = await get_filtered_rag(body.message, db, body.admin)

    log.info(
        "chat conv=%s sources=%d rag_chunks=%d admin=%s",
        conv.id, len(data_contexts), len(rag_context), body.admin,
    )

    # ask the model — get_ai_response already handles its own errors
    reply_text = await get_ai_response(
        history,
        data_contexts=data_contexts or None,
        rag_context=rag_context or None,
    )

    # persist the reply
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=reply_text)
    db.add(assistant_msg)
    try:
        db.commit()
        db.refresh(assistant_msg)
    except SQLAlchemyError:
        db.rollback()
        log.exception("failed to persist assistant reply")
        raise HTTPException(status_code=500, detail="Could not save assistant reply")

    # build citations: dedupe document filenames in the order they appeared
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
