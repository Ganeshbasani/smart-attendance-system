"""
Scheduling calculations: late arrival, early departure, worked time, leave.

Pure functions over shift/attendance values so the logic is testable without
HTTP or a database, plus one small query helper for the leave check used by
the bulk absent-marking run.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import LeaveRequest, Shift, User


def _combine(day: date, t: time) -> datetime:
    return datetime.combine(day, t)


def is_late(time_in: Optional[time], shift: Optional[Shift], day: Optional[date]) -> Optional[bool]:
    """
    True when arrival is after start_time + grace_minutes.

    Returns None when it cannot be judged (no shift, no time_in, or no date),
    which the schema exposes as NULL = "not applicable".
    """
    if shift is None or time_in is None or day is None:
        return None
    deadline = _combine(day, shift.start_time) + timedelta(minutes=shift.grace_minutes)
    return _combine(day, time_in) > deadline


def is_early_leave(
    time_out: Optional[time], shift: Optional[Shift], day: Optional[date]
) -> Optional[bool]:
    """
    True when leaving before shift end_time.

    Grace applies to arrival only (documented behaviour). None when not
    judgeable.
    """
    if shift is None or time_out is None or day is None:
        return None
    return _combine(day, time_out) < _combine(day, shift.end_time)


def worked_minutes(time_in: Optional[time], time_out: Optional[time]) -> Optional[int]:
    """Minutes between check-in and check-out, or None if either is missing."""
    if time_in is None or time_out is None:
        return None
    delta = _combine(date.today(), time_out) - _combine(date.today(), time_in)
    minutes = int(delta.total_seconds() // 60)
    # A checkout recorded before check-in (clock skew) is not a negative shift.
    return max(minutes, 0)


def has_approved_leave(db: Session, user_id: int, day: date) -> bool:
    """True when an approved leave request covers `day` for `user_id`."""
    return (
        db.query(LeaveRequest.id)
        .filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= day,
            LeaveRequest.end_date >= day,
        )
        .first()
        is not None
    )


def user_is_on_leave(db: Session, user: User, day: date) -> bool:
    return has_approved_leave(db, user.id, day)
