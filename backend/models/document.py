from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Document(Base):
    # one row per uploaded / seeded document
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    # uuid we generate at upload time — used as the chroma metadata key
    doc_id: Mapped[str] = mapped_column(unique=True, index=True)
    # original name (used for citations in chat replies)
    filename: Mapped[str]
    file_type: Mapped[str]
    # how many chunks ended up in the vector store
    chunk_count: Mapped[int] = mapped_column(default=0)
    # "pending" | "ingested" | "failed"
    status: Mapped[str] = mapped_column(default="pending")
    # "public" | "internal" — gates retrieval in non-admin mode
    sensitivity: Mapped[str] = mapped_column(default="public")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
