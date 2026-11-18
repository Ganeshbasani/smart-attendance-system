"""
Scheduling domain: shifts, holidays, leave, and attendance corrections.

Shifts define when a work day starts/ends and how many minutes of grace apply
to arrival. Holidays and approved leave suppress the bulk "mark absent" run.
Correction requests let users propose a fix to one of their attendance rows;
an admin must approve it before anything changes.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.time_utils import utc_now_naive
from app.db.base import Base


class Shift(Base):
    """A work schedule window (e.g. 09:00–17:30 with 15 min grace)."""

    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    # Minutes after start_time during which arrival is still "on time".
    grace_minutes = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now_naive)

    users = relationship("User", back_populates="shift")


class Holiday(Base):
    """A non-working day. Bulk absent-marking skips these."""

    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)


class LeaveRequest(Base):
    """
    A user's leave application for a date range.

    While status is 'pending' it changes nothing; once 'approved' the bulk
    absent-marking run skips the user for every date in [start_date, end_date].
    """

    __tablename__ = "leave_requests"
    __table_args__ = (
        Index("ix_leave_requests_status", "status"),
        Index("ix_leave_requests_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    leave_type = Column(String, nullable=False, default="annual")  # annual|sick|other
    reason = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending|approved|rejected
    review_note = Column(Text, nullable=True)
    reviewed_by = Column(Integer, nullable=True)  # admin user id
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    user = relationship("User", back_populates="leave_requests")


class AttendanceCorrectionRequest(Base):
    """
    A user's proposal to fix one of their attendance rows.

    Approval applies the proposed values to the attendance record; rejection
    only records the decision. One pending request per attendance row.
    """

    __tablename__ = "attendance_correction_requests"
    __table_args__ = (
        Index("ix_correction_requests_status", "status"),
        Index("ix_correction_requests_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attendance_id = Column(
        Integer, ForeignKey("attendance.id", ondelete="CASCADE"), nullable=False
    )
    proposed_status = Column(String, nullable=False)  # present|absent
    proposed_time_in = Column(Time, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending|approved|rejected
    review_note = Column(Text, nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    user = relationship("User", back_populates="correction_requests")
    attendance = relationship("Attendance")
