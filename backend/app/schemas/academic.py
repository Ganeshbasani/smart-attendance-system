"""Request/response schemas for the academic domain (API v1)."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: Optional[str] = Field(default=None, max_length=32)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: Optional[str] = None
    created_at: datetime


class AcademicSessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_date: date
    end_date: date
    is_active: bool = False


class AcademicSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=32)
    department_id: Optional[int] = None
    credits: int = Field(default=0, ge=0, le=40)


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    department_id: Optional[int] = None
    credits: int
    created_at: datetime


class TeacherCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=120)
    employee_id: str = Field(min_length=1, max_length=64)
    department_id: Optional[int] = None
    phone_number: Optional[str] = None


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    employee_id: str
    department_id: Optional[int] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    created_at: datetime


class TeacherUpdate(BaseModel):
    """Partial update — the account password is never changed here."""
    employee_id: Optional[str] = Field(default=None, min_length=1, max_length=64)
    department_id: Optional[int] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone_number: Optional[str] = None


class StudentCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=120)
    roll_number: str = Field(min_length=1, max_length=64)
    phone_number: Optional[str] = None
    department_id: Optional[int] = None
    academic_session_id: Optional[int] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    roll_number: str
    department_id: Optional[int] = None
    academic_session_id: Optional[int] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    created_at: datetime


class StudentUpdate(BaseModel):
    """Partial update — the account password is never changed here."""
    roll_number: Optional[str] = Field(default=None, min_length=1, max_length=64)
    department_id: Optional[int] = None
    academic_session_id: Optional[int] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone_number: Optional[str] = None


class ClassSectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=32)
    course_id: Optional[int] = None
    teacher_id: Optional[int] = None
    academic_session_id: Optional[int] = None


class ClassSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    course_id: Optional[int] = None
    teacher_id: Optional[int] = None
    academic_session_id: Optional[int] = None
    student_count: int = 0
    created_at: datetime


class EnrollRequest(BaseModel):
    student_id: int = Field(gt=0)


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    class_section_id: int
    student_id: int
    roll_number: Optional[str] = None
    full_name: Optional[str] = None
    created_at: datetime
