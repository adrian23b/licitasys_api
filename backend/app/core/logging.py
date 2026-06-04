import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str) -> None:
    """Configure structured JSON logging for the application."""

    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **context: Any) -> structlog.stdlib.BoundLogger:
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger
