from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

# SQLite needs check_same_thread=False; other DBs don't support that arg
_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # Keep a small pool; fine-tune for Postgres in production
    pool_pre_ping=True,   # drops stale connections before use
    pool_size=5 if not _is_sqlite else 1,
    max_overflow=10 if not _is_sqlite else 0,
)

# Enable WAL mode for SQLite — allows concurrent reads alongside writes
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_wal(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create all tables. Called once at startup from main.py."""
    from models import Conversation, Document, Message  # noqa: F401 — imports register all on Base

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
