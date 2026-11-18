"""
Audit logging service.

Writes one ``AuditLog`` row per security-relevant action. Callers supply the
actor (when authenticated) and a short action/entity description; client
metadata is taken from the request context set by the middleware.

Audit writing must never break the user-facing operation, so failures are
logged and swallowed. When ``AUDIT_LOG_ENABLED`` is false the service is a
no-op.
"""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_context import get_request_context
from app.models import AuditLog, User

logger = logging.getLogger("smart_attendance.audit")


def _actor_fields(actor: Optional[User]):
    if actor is None:
        return None, None
    return getattr(actor, "id", None), getattr(actor, "email", None)


def record(
    db: Session,
    *,
    action: str,
    actor: Optional[User] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Persist an audit entry. Commits immediately and never raises."""
    if not settings.AUDIT_LOG_ENABLED:
        return

    ctx = get_request_context()
    actor_id, actor_email = _actor_fields(actor)

    try:
        db.add(AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=ip_address if ip_address is not None else ctx.ip_address,
            user_agent=user_agent if user_agent is not None else ctx.user_agent,
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to write audit log for action %s", action)
