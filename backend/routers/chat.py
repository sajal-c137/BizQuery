from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Conversation, Message, User
from routers.users import get_current_user
from schemas import ChatRequest, ChatResponse, ConversationDetail, ConversationOut, MessageOut
from services.ai import get_ai_response

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_conversation(conv_id: int, user: User, db: Session) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.created_at.desc()).all()


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_conversation(conv_id, current_user, db)


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conv_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = _get_conversation(conv_id, current_user, db)
    db.delete(conv)
    db.commit()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resolve or create conversation
    if body.conversation_id:
        conv = _get_conversation(body.conversation_id, current_user, db)
    else:
        conv = Conversation(user_id=current_user.id, title=body.message[:60])
        db.add(conv)
        db.flush()

    # Persist user message
    user_msg = Message(conversation_id=conv.id, role="user", content=body.message)
    db.add(user_msg)
    db.flush()

    # Build history for OpenAI
    history = [{"role": m.role, "content": m.content} for m in conv.messages if m.id != user_msg.id]
    history.append({"role": "user", "content": body.message})

    # Get AI reply
    reply_text = await get_ai_response(history)

    # Persist assistant message
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=reply_text)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return {"conversation_id": conv.id, "message": MessageOut.model_validate(assistant_msg)}
