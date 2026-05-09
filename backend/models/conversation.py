from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

# avoid a circular import — Message references back here
if TYPE_CHECKING:
    from models.message import Message


class Conversation(Base):
    # one row per chat thread
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # auto-titled from the first message
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    # always UTC
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # cascade delete -> dropping a conversation drops its messages
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
