from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings
from logger import get_logger

log = get_logger("db")

# SQLite quirk: needs check_same_thread=False for FastAPI's threadpool
_is_sqlite = settings.database_url.startswith("sqlite")

# build the engine — small pool for sqlite, normal pool otherwise
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,                       # drop stale conns
    pool_size=1 if _is_sqlite else 5,
    max_overflow=0 if _is_sqlite else 10,
)

# enable WAL for sqlite — concurrent reads while writing
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        try:
            dbapi_conn.execute("PRAGMA journal_mode=WAL")
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
        except Exception as e:
            # not fatal — just log
            log.warning("sqlite pragma setup failed: %s", e)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # called once at startup
    # imports register all models on Base
    from models import Conversation, Document, Message  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        log.info("schema ready (tables created if missing)")
    except SQLAlchemyError:
        log.exception("failed to create schema")
        raise

    # poor-man's migration for sqlite — adds the sensitivity column on
    # older DBs without forcing a full alembic run. Postgres should use alembic.
    if _is_sqlite:
        try:
            with engine.begin() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(documents)"))}
                if "sensitivity" not in cols:
                    log.info("backfilling 'sensitivity' column on documents table")
                    conn.execute(text(
                        "ALTER TABLE documents "
                        "ADD COLUMN sensitivity TEXT NOT NULL DEFAULT 'public'"
                    ))
        except SQLAlchemyError:
            log.exception("sensitivity backfill failed")
            # don't crash startup over this — the app still works for new DBs
            pass


def get_db():
    # FastAPI dependency — yields a session, always closes
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
