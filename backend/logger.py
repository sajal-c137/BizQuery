import logging
import os
import sys

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

# configure once at import time
_root = logging.getLogger("bizquery")
if not _root.handlers:
    _root.addHandler(_handler)
    _root.setLevel(getattr(logging, _LEVEL, logging.INFO))
    _root.propagate = False


def get_logger(name: str) -> logging.Logger:
    # child loggers inherit handlers from "bizquery"
    return logging.getLogger(f"bizquery.{name}")
