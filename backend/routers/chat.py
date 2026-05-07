from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Conversation, Message
from schemas import ChatRequest, ChatResponse, ConversationDetail, ConversationOut, MessageOut
from services.ai import get_ai_response

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

    reply_text = await get_ai_response(history)

    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=reply_text)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return {"conversation_id": conv.id, "message": MessageOut.model_validate(assistant_msg)}
