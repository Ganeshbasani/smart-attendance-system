from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
)

from app.core.time_utils import utc_now_naive
from app.db.base import Base


class AuditLog(Base):
    """
    Append-only record of security-relevant actions.

    Written by the audit service after authentication, admin management, face
    enrollment, and attendance marking. Never expose raw biometric data here;
    ``details`` should contain only identifiers and human-readable context.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, nullable=True, index=True)
    actor_email = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=True, index=True)
    entity_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive, index=True)
