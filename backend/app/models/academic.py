"""Academic domain models (Phase 2 of the AttendX program).

Additive tables only: nothing in the existing attendance/recognition schema
is changed. ``users.role`` gains the values ``teacher`` and ``student``;
legacy ``user`` rows are migrated to ``student`` by alembic.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.time_utils import utc_now_naive
from app.db.base import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    code = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    courses = relationship("Course", back_populates="department")


class OrganizationSettings(Base):
    """Single-tenant workspace profile and sector-specific labels."""
    __tablename__ = "organization_settings"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, default="My Organization")
    sector = Column(String, nullable=False, default="other")  # school | college | office | other
    has_sections = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class AcademicSession(Base):
    """An academic term (e.g. '2026-27 Odd Semester'), not an attendance session."""

    __tablename__ = "academic_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    credits = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    department = relationship("Department", back_populates="courses")
    classes = relationship("ClassSection", back_populates="course")


class Teacher(Base):
    """Staff profile attached to a ``users`` row with role ``teacher``."""

    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    employee_id = Column(String, unique=True, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    user = relationship("User", back_populates="teacher_profile")
    department = relationship("Department")
    classes = relationship("ClassSection", back_populates="teacher")


class Student(Base):
    """Student profile attached to a ``users`` row with role ``student``."""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    roll_number = Column(String, unique=True, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    academic_session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    user = relationship("User", back_populates="student_profile")
    enrollments = relationship("ClassEnrollment", back_populates="student", cascade="all, delete-orphan")


class ClassSection(Base):
    """A taught class (a course offering in a term). Table name: ``classes``."""

    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    level = Column(String, nullable=True, index=True)  # grade, program, team, or department label
    section = Column(String, nullable=True, index=True)  # NULL is valid for no-section organizations
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    academic_session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    course = relationship("Course", back_populates="classes")
    teacher = relationship("Teacher", back_populates="classes")
    enrollments = relationship("ClassEnrollment", back_populates="class_section", cascade="all, delete-orphan")


class ClassEnrollment(Base):
    """Join table linking students to classes. One row per (class, student)."""

    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint("class_section_id", "student_id", name="uq_class_student"),
    )

    id = Column(Integer, primary_key=True, index=True)
    class_section_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now_naive)

    class_section = relationship("ClassSection", back_populates="enrollments")
    student = relationship("Student", back_populates="enrollments")
