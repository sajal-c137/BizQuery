from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

# back-ref only — guarded to avoid circular imports at runtime
if TYPE_CHECKING:
    from models.conversation import Conversation


class Message(Base):
    # one row per chat message (user or assistant)
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    # "user" | "assistant"
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # may be long — Text rather than VARCHAR
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
