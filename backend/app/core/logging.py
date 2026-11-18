"""Logging configuration."""

import logging

from app.core.config import settings
from app.core.request_context import get_request_context

# Third-party loggers that are far too chatty at DEBUG level.
_NOISY_LOGGERS = (
    "multipart",
    "multipart.multipart",
    "python_multipart",
    "watchfiles",
    "watchfiles.main",
)


class RequestContextFilter(logging.Filter):
    """Inject the current correlation id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_context().request_id
        return True


def configure_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
    )
    # Keep our own logs at the chosen level but silence noisy libraries.
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    # The filter must live on the HANDLERS, not the root logger: a logger's
    # filters only run for records emitted directly by that logger, while
    # propagated records (httpx, sqlalchemy, ...) go straight to the handlers.
    # A handler-side filter guarantees %(request_id)s exists for every record
    # that reaches our format string.
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(f, RequestContextFilter) for f in handler.filters):
            handler.addFilter(RequestContextFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
