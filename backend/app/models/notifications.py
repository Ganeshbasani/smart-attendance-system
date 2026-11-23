"""
In-app notifications for the current user.

One row per message (e.g. "your leave request was approved"). Rows are always
read/written scoped to a single user; the API never exposes another user's
notifications. Email delivery is a separate, optional best-effort channel in
app.services.notifications — this table is the source of truth.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.time_utils import utc_now_naive
from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # The hot query is "my unread count" and "my recent list".
        Index("ix_notifications_user_id_is_read", "user_id", "is_read"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Short machine type, e.g. leave_decision | correction_decision | shift_assigned.
    type = Column(String, nullable=False, default="info")
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    # Optional pointer to what this is about (entity_type + entity_id).
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utc_now_naive, index=True)
    read_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notifications")
