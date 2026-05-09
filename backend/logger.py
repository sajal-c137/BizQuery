import logging
import os
import sys
from collections import deque

# central logger for the whole backend
# log level is configurable via env (LOG_LEVEL=DEBUG|INFO|WARNING|...)
_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# stream to stdout so docker logs picks it up cleanly
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)

# in-memory ring buffer — drives the /logs endpoint shown in the UI
# bounded so a long-running container can't OOM
_BUFFER_SIZE = int(os.getenv("LOG_BUFFER_SIZE", "1000"))
_buffer: deque = deque(maxlen=_BUFFER_SIZE)
_ts_fmt = logging.Formatter(datefmt="%Y-%m-%d %H:%M:%S")


class _RingHandler(logging.Handler):
    """Pushes structured log records into the in-memory ring."""

    def emit(self, record: logging.LogRecord) -> None:
        # never let a logging failure crash the caller
        try:
            msg = record.getMessage()
            if record.exc_info:
                # include traceback for exception logs
                msg += "\n" + _ts_fmt.formatException(record.exc_info)
            _buffer.append({
                "time": _ts_fmt.formatTime(record, "%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "name": record.name,
                "message": msg,
            })
        except Exception:
            pass


_ring = _RingHandler()

# configure once at import time
_root = logging.getLogger("bizquery")
if not _root.handlers:
    _root.addHandler(_handler)
    _root.addHandler(_ring)
    _root.setLevel(getattr(logging, _LEVEL, logging.INFO))
    _root.propagate = False


def get_logger(name: str) -> logging.Logger:
    # child loggers inherit handlers from "bizquery"
    return logging.getLogger(f"bizquery.{name}")


def get_buffered_logs(limit: int | None = None) -> list[dict]:
    # snapshot the deque (safe under concurrent appends)
    items = list(_buffer)
    if limit and limit > 0:
        items = items[-limit:]
    return items
