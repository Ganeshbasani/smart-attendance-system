"""Attendance session + verification decision models (AttendX Phase 7).

Additive: the existing per-day ``attendance`` table is untouched. Session
records carry one decision per student per session, and verification events
keep the inputs that produced each decision (for review and analytics).
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.time_utils import utc_now_naive
from app.db.base import Base


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    class_section_id = Column(Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String, nullable=False, index=True)
    # draft | active | closed
    status = Column(String, nullable=False, default="draft", index=True)
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    class_section = relationship("ClassSection")
    records = relationship(
        "SessionAttendance", back_populates="session", cascade="all, delete-orphan"
    )


class SessionAttendance(Base):
    """Decision outcome for one student in one session (one row per pair)."""

    __tablename__ = "session_attendance"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # VERIFIED | REVIEW_REQUIRED | REJECTED | DUPLICATE | MANUAL_OVERRIDE
    decision = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    liveness_ok = Column(Boolean, nullable=True)
    reason = Column(Text, nullable=True)
    # Teacher/admin who made a manual override / reviewed a decision.
    marked_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    marked_at = Column(DateTime, default=utc_now_naive)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    session = relationship("AttendanceSession", back_populates="records")
    user = relationship("User", foreign_keys=[user_id])
    marker = relationship("User", foreign_keys=[marked_by])


class VerificationEvent(Base):
    """Append-only log of every decision attempt (inputs + outcome).

    Never exposes raw biometric data: only scores, booleans, thresholds, and
    the model version that made the call.
    """

    __tablename__ = "verification_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_unique_id = Column(String, nullable=True)  # stable identifier if user unresolved
    event_type = Column(String, nullable=False, default="mark")  # mark | manual | review
    decision = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    liveness_ok = Column(Boolean, nullable=True)
    model_version = Column(String, nullable=True)
    threshold = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive, index=True)
