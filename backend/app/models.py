from datetime import datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))

class Section(Base):
    __tablename__ = "sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    year: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    department: Mapped[Department] = relationship()

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(140))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    year: Mapped[int] = mapped_column(Integer)
    department: Mapped[Department] = relationship()
    section: Mapped[Section] = relationship()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(140))
    role: Mapped[str] = mapped_column(String(20), index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.student_id"), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(140))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    semester: Mapped[str] = mapped_column(String(50))
    threshold: Mapped[float] = mapped_column(Float, default=75.0)
    planned_sessions: Mapped[int] = mapped_column(Integer, default=32)

class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    __table_args__ = (UniqueConstraint("student_id", "subject_id", name="uq_enrollment"),)

class FacultyAssignment(Base):
    __tablename__ = "faculty_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    __table_args__ = (UniqueConstraint("faculty_user_id", "subject_id", "section_id", name="uq_faculty_assignment"),)

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    faculty_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    room: Mapped[str] = mapped_column(String(80), default="")

class AcademicCalendar(Base):
    __tablename__ = "academic_calendar"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(30))
    label: Mapped[str] = mapped_column(String(140))

class ClassSession(Base):
    __tablename__ = "class_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    faculty_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_date: Mapped[datetime] = mapped_column(Date)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(20), default="open")
    qr_secret: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"))
    status: Mapped[str] = mapped_column(String(20))
    marked_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    source: Mapped[str] = mapped_column(String(30))
    device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    token_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_attendance"),)

class AttendanceAttempt(Base):
    __tablename__ = "attendance_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("class_sessions.id"), nullable=True)
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.student_id"), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    token_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"))
    device_hash: Mapped[str] = mapped_column(String(128))
    label: Mapped[str] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("student_id", "device_hash", name="uq_device"),)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.student_id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Intervention(Base):
    __tablename__ = "interventions"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"))
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id"), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(60))
    recommendation: Mapped[str] = mapped_column(Text)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Open")
    due_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class CorrectionRequest(Base):
    __tablename__ = "correction_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"))
    requested_status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    document_name: Mapped[str | None] = mapped_column(String(220), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class CondonationRequest(Base):
    __tablename__ = "condonation_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    reason: Mapped[str] = mapped_column(Text)
    document_name: Mapped[str | None] = mapped_column(String(220), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class SyncEvent(Base):
    __tablename__ = "sync_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_event_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
