"""
Per-request context (correlation id, client metadata).

Set once by the request-id middleware in ``app.main`` and read anywhere in the
request handling path — logging, audit records, error responses — without
threading a ``Request`` object through every service signature.
"""

import contextvars
from dataclasses import dataclass
from typing import Optional


@dataclass
class RequestContext:
    request_id: str = "-"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


_ctx: contextvars.ContextVar[RequestContext] = contextvars.ContextVar(
    "request_context", default=RequestContext()
)


def set_request_context(context: RequestContext):
    """Bind a context for the current async task. Returns a reset token."""
    return _ctx.set(context)


def reset_request_context(token) -> None:
    _ctx.reset(token)


def get_request_context() -> RequestContext:
    return _ctx.get()
