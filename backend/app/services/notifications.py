"""
Notification service: in-app rows plus an optional best-effort email copy.

Design rules (mirrors app.services.audit):
  * A notification failure must NEVER break the operation that triggered it —
    everything here is wrapped, logged, and swallowed.
  * The in-app row is the source of truth; email is a secondary channel that
    is off unless EMAIL_NOTIFY_ENABLED=true and SMTP_HOST is configured.
  * Email uses the standard library only (smtplib) — no new dependencies.
    It is sent synchronously with a short timeout because this stack has no
    task queue; a slow SMTP server costs at most SMTP_TIMEOUT_SECONDS and a
    logged warning, never a failed request.
"""

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Notification, User

logger = logging.getLogger("smart_attendance.notifications")


def notify(
    db: Session,
    *,
    user_id: int,
    type: str,
    title: str,
    message: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    email_to: Optional[str] = None,
) -> None:
    """
    Record an in-app notification for one user and, if configured, email a
    copy. Commits immediately and never raises.
    """
    if not settings.NOTIFICATIONS_ENABLED:
        return

    try:
        db.add(
            Notification(
                user_id=user_id,
                type=type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist notification for user %s", user_id)
        return

    if settings.EMAIL_NOTIFY_ENABLED:
        _send_email(to=email_to, title=title, message=message)


def _send_email(*, to: Optional[str], title: str, message: str) -> None:
    """Best-effort email copy. Never raises; logs success and failure."""
    if not settings.SMTP_HOST:
        logger.warning(
            "EMAIL_NOTIFY_ENABLED is true but SMTP_HOST is empty — skipping email"
        )
        return
    if not to:
        logger.warning("No recipient address for notification email — skipping")
        return

    sender = settings.SMTP_FROM or settings.SMTP_USERNAME
    if not sender:
        logger.warning("No SMTP_FROM/SMTP_USERNAME sender address — skipping email")
        return

    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(message)

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS
        ) as smtp:
            if settings.SMTP_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info("Notification email sent to %s", to)
    except Exception:
        # The in-app row already exists; email is supplementary.
        logger.exception("Failed to send notification email to %s", to)
