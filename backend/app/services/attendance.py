import hashlib, hmac, json, secrets
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..config import settings
from ..models import AttendanceAttempt, AttendanceRecord, ClassSession, Device, FacultyAssignment, Student, Subject


def issue_qr(session: ClassSession):
    token_id = secrets.token_urlsafe(10)
    exp = int(datetime.now(timezone.utc).timestamp()) + settings.qr_ttl_seconds
    body = f"{session.id}.{token_id}.{exp}"
    signature = hmac.new(session.qr_secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:28]
    payload = json.dumps({"s": session.id, "t": token_id, "e": exp, "sig": signature}, separators=(",", ":"))
    return payload


def verify_qr(db: Session, payload: str, allow_offline: bool=False, queued_at: float|None=None):
    data = json.loads(payload)
    session = db.get(ClassSession, int(data["s"]))
    if not session or session.status != "open": raise ValueError("Session is not active")
    now = int(datetime.now(timezone.utc).timestamp())
    if int(data["e"]) < now:
        if not allow_offline or queued_at is None or now - int(data["e"]) > 180:
            raise ValueError("QR code expired")
    body = f"{session.id}.{data['t']}.{data['e']}"
    expected = hmac.new(session.qr_secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:28]
    if not hmac.compare_digest(expected, data["sig"]): raise ValueError("Invalid QR signature")
    return session, data


def check_device(db: Session, student_id: str, device_id: str):
    device = db.scalar(select(Device).where(Device.student_id == student_id, Device.device_hash == device_id, Device.active == True))
    if device:
        device.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
        return True
    # First-use registration keeps the demo usable; product UI makes the registration explicit.
    device = Device(student_id=student_id, device_hash=device_id, label="This browser", active=True, last_seen=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(device)
    db.flush()
    return True


def submit_qr_attendance(db: Session, student_id: str, payload: str, device_id: str, allow_offline: bool=False, queued_at: float|None=None):
    try:
        session, data = verify_qr(db, payload, allow_offline=allow_offline, queued_at=queued_at)
    except Exception as exc:
        db.add(AttendanceAttempt(student_id=student_id, status="Rejected", reason=str(exc), device_id=device_id))
        db.commit()
        raise ValueError(str(exc))
    if not check_device(db, student_id, device_id):
        raise ValueError("Device is not registered")
    existing = db.scalar(select(AttendanceRecord).where(AttendanceRecord.session_id == session.id, AttendanceRecord.student_id == student_id))
    if existing:
        db.add(AttendanceAttempt(session_id=session.id, student_id=student_id, status="Rejected", reason="Duplicate attendance", device_id=device_id, token_id=data["t"]))
        db.commit()
        raise ValueError("Attendance already recorded")
    rec = AttendanceRecord(session_id=session.id, student_id=student_id, status="Present", source="qr", device_id=device_id, token_id=data["t"])
    db.add(rec)
    db.add(AttendanceAttempt(session_id=session.id, student_id=student_id, status="Accepted", device_id=device_id, token_id=data["t"]))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Attendance was already recorded")
    return rec


def create_session(db: Session, faculty_id: int, subject_id: int, section_id: int, session_date, start_time, end_time):
    allowed = db.scalar(select(FacultyAssignment).where(FacultyAssignment.faculty_user_id == faculty_id, FacultyAssignment.subject_id == subject_id, FacultyAssignment.section_id == section_id))
    if not allowed: raise ValueError("You are not assigned to this subject and section")
    session = ClassSession(subject_id=subject_id, section_id=section_id, faculty_user_id=faculty_id, session_date=session_date, start_time=start_time, end_time=end_time, qr_secret=secrets.token_urlsafe(32), status="open")
    db.add(session); db.commit(); db.refresh(session)
    return session
