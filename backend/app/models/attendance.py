from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.time_utils import utc_now_naive
from app.db.base import Base


class Attendance(Base):
    __tablename__ = "attendance"

    __table_args__ = (
        # One attendance row per user per day. Enforced by the database so two
        # concurrent marks cannot both pass the application-level "already
        # marked today" check and insert duplicate rows.
        UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
        # Date-only lookups (analytics periods, admin date filter) are the
        # hottest query path and are not covered by the unique constraint's
        # index, which is ordered (user_id, date).
        Index("ix_attendance_date", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    time_in = Column(Time, nullable=True)
    time_out = Column(Time, nullable=True)  # set by POST /attendance/checkout
    status = Column(String, nullable=False)  # "present" or "absent"
    # Late/early flags are computed from the user's shift at mark/checkout
    # time. NULL means "not applicable" (no shift assigned), not "on time".
    is_late = Column(Boolean, nullable=True)
    is_early_leave = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    user = relationship("User", back_populates="attendances")
