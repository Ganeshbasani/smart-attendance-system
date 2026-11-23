"""Current-user notification endpoints (list, unread count, mark read)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.core.time_utils import utc_now_naive
from app.db.session import get_db
from app.models import Notification, User

logger = logging.getLogger("smart_attendance.notifications")

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "entity_type": n.entity_type,
        "entity_id": n.entity_id,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "read_at": n.read_at.isoformat() if n.read_at else None,
    }


@router.get("")
async def list_notifications(
    response: Response,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    The current user's notifications, newest first.

    Always scoped to the authenticated user — there is no parameter to read
    anyone else's notifications. X-Total-Count carries the total matching rows
    (before paging).
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)  # noqa: E712
    total = query.count()
    rows = (
        query.order_by(Notification.id.desc()).offset(offset).limit(limit).all()
    )
    response.headers["X-Total-Count"] = str(total)
    return [_dict(r) for r in rows]


@router.get("/unread-count")
async def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Number of unread notifications for the current user (badge source)."""
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .count()
    )
    return {"count": count}


@router.post("/read-all")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Mark every unread notification of the current user as read."""
    from sqlalchemy import update

    result = db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True, read_at=utc_now_naive())
    )
    db.commit()
    return {"updated": result.rowcount or 0}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Mark one notification read.

    Another user's notification is reported as 404 (not 403) so notification
    ids cannot be probed for existence.
    """
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = utc_now_naive()
        db.commit()
    return _dict(notification)
