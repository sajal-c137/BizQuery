from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(unique=True, index=True)
    filename: Mapped[str]
    file_type: Mapped[str]
    chunk_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="pending")
    sensitivity: Mapped[str] = mapped_column(default="public")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
