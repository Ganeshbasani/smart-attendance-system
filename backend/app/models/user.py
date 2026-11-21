from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.time_utils import utc_now_naive
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    unique_id = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=True)
    department = Column(String, nullable=True)
    # Roles: admin, teacher, student. Legacy "user" is migrated to "student"
    # by alembic; permission checks treat both as non-staff for compatibility.
    role = Column(String, default="student", nullable=False)
    is_active = Column(Boolean, default=True)
    face_registered = Column(Boolean, default=False)
    face_encoding_path = Column(String, nullable=True)
    # Optional work schedule. NULL → late/early flags are not computed.
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now_naive)

    attendances = relationship("Attendance", back_populates="user")
    face_embedding = relationship(
        "FaceEmbedding", back_populates="user", uselist=False,
        cascade="all, delete-orphan",
    )
    face_images = relationship(
        "FaceImage", back_populates="user", cascade="all, delete-orphan",
    )
    shift = relationship("Shift", back_populates="users")
    leave_requests = relationship(
        "LeaveRequest", back_populates="user", cascade="all, delete-orphan"
    )
    correction_requests = relationship(
        "AttendanceCorrectionRequest", back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan",
    )
    student_profile = relationship(
        "Student", back_populates="user", uselist=False,
        cascade="all, delete-orphan",
    )
    teacher_profile = relationship(
        "Teacher", back_populates="user", uselist=False,
        cascade="all, delete-orphan",
    )
