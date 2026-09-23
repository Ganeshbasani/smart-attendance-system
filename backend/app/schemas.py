from datetime import date
from typing import Any
from pydantic import BaseModel, Field

class LoginIn(BaseModel):
    username: str
    password: str

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class QRScanIn(BaseModel):
    qr_payload: str
    device_id: str = Field(min_length=8, max_length=160)

class SessionCreateIn(BaseModel):
    subject_id: int
    section_id: int
    session_date: date
    start_time: str
    end_time: str

class AttendanceMarkIn(BaseModel):
    student_id: str
    status: str = Field(pattern="^(Present|Absent|Excused)$")
    device_id: str | None = None
    source: str = "faculty"

class CorrectionIn(BaseModel):
    session_id: int
    requested_status: str = Field(pattern="^(Present|Absent|Excused)$")
    reason: str = Field(min_length=8, max_length=1000)
    document_name: str | None = None

class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(Approved|Rejected)$")
    note: str = Field(default="", max_length=1000)

class InterventionIn(BaseModel):
    student_id: str
    subject_id: int | None = None
    trigger_type: str
    recommendation: str
    owner_user_id: int | None = None
    due_date: date | None = None

class InterventionUpdateIn(BaseModel):
    status: str | None = Field(default=None, pattern="^(Open|In Progress|Resolved)$")
    notes: str | None = None
    outcome: str | None = None

class CondonationIn(BaseModel):
    subject_id: int
    reason: str = Field(min_length=8, max_length=1000)
    document_name: str | None = None

class SyncEventIn(BaseModel):
    client_event_id: str
    payload: dict[str, Any]
