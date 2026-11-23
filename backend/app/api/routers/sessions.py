"""Attendance sessions + decision-engine API (AttendX Module 5/10).

All paths are versioned under /api/v1. Sessions are additive: the legacy
per-day kiosk attendance flow is unchanged. Every decision is logged as a
verification event with its inputs (never raw biometrics).
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.core.time_utils import now_local
from app.db.session import get_db
from app.models import (
    AttendanceSession,
    ClassEnrollment,
    ClassSection,
    SessionAttendance,
    Student,
    Teacher,
    User,
    VerificationEvent,
)
from app.schemas import (
    DecisionOut,
    DecisionRequest,
    EventOut,
    ManualOverrideRequest,
    ReviewRequestManual,
    SessionCreate,
    SessionOut,
    ManualAttendanceBatch,
)
from app.services import decision as engine
from app.services.audit import record as audit_record

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _get_session_or_404(db: Session, session_id: int) -> AttendanceSession:
    obj = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return obj


def _can_manage(user: User, session: AttendanceSession, db: Session) -> bool:
    """Admins manage any session; teachers manage their own class sessions."""
    if user.role == "admin":
        return True
    if user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        return bool(teacher and session.class_section_id and
                    db.query(ClassSection).filter(
                        ClassSection.id == session.class_section_id,
                        ClassSection.teacher_id == teacher.id,
                    ).first())
    return False


def _require_manager(user: User, session: AttendanceSession, db: Session) -> None:
    if not _can_manage(user, session, db):
        raise HTTPException(status_code=403, detail="You cannot manage this session")


def _is_enrolled(user_id: int, session: AttendanceSession, db: Session) -> bool:
    if session.class_section_id is None:
        # Classless sessions are explicit open sessions created by staff.
        return True
    return db.query(ClassEnrollment.id).join(
        Student, ClassEnrollment.student_id == Student.id
    ).filter(
        Student.user_id == user_id,
        ClassEnrollment.class_section_id == session.class_section_id,
    ).first() is not None


def _require_viewer(user: User, session: AttendanceSession, db: Session) -> None:
    if user.role == "admin" or _can_manage(user, session, db):
        return
    if user.role in ("student", "user") and _is_enrolled(user.id, session, db):
        return
    # Do not reveal whether a session outside the caller's scope exists.
    raise HTTPException(status_code=404, detail="Session not found")


def _log_event(db: Session, record: SessionAttendance, event_type: str,
               confidence, quality, liveness, threshold, reason, actor: User,
               model_version: str = None):
    db.add(VerificationEvent(
        session_id=record.session_id, user_id=record.user_id,
        user_unique_id=actor.unique_id if actor else None,
        event_type=event_type, decision=record.decision,
        confidence=confidence, quality_score=quality, liveness_ok=liveness,
        model_version=model_version, threshold=threshold, reason=reason,
    ))


def _record_out(record: SessionAttendance) -> DecisionOut:
    return DecisionOut(
        id=record.id, session_id=record.session_id, user_id=record.user_id,
        decision=record.decision, attendance_status=record.attendance_status,
        confidence=record.confidence,
        quality_score=record.quality_score, liveness_ok=record.liveness_ok,
        reason=record.reason, marked_at=record.marked_at,
    )


# ── session lifecycle ─────────────────────────────────────────────────────────

@router.get("", response_model=list[SessionOut])
async def list_sessions(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    class_section_id: Optional[int] = Query(None, gt=0),
    mode: Optional[str] = Query(None, pattern="^(manual|biometric)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    query = db.query(AttendanceSession)
    if class_section_id is not None:
        query = query.filter(AttendanceSession.class_section_id == class_section_id)
    if mode is not None:
        query = query.filter(AttendanceSession.attendance_mode == mode)
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher is None:
            return []
        query = query.join(ClassSection, AttendanceSession.class_section_id == ClassSection.id).filter(
            ClassSection.teacher_id == teacher.id
        )
    elif current_user.role in ("student", "user"):
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student is None:
            return []
        query = query.outerjoin(
            ClassEnrollment, ClassEnrollment.class_section_id == AttendanceSession.class_section_id
        ).filter(
            (AttendanceSession.class_section_id.is_(None))
            | (ClassEnrollment.student_id == student.id)
        )
    elif current_user.role != "admin":
        return []
    return query.order_by(AttendanceSession.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/reports/manual")
async def manual_attendance_report(
    class_section_id: int = Query(gt=0),
    group_by: str = Query("day", pattern="^(day|month|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    """Return finalized present/absent percentages for one authorized class."""
    section = db.query(ClassSection).filter(ClassSection.id == class_section_id).first()
    if section is None:
        raise HTTPException(status_code=404, detail="Class not found")
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher is None or section.teacher_id != teacher.id:
            raise HTTPException(status_code=403, detail="You cannot view reports for this class")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")

    sessions = db.query(AttendanceSession).filter(
        AttendanceSession.class_section_id == class_section_id,
        AttendanceSession.attendance_mode == "manual",
        AttendanceSession.status == "closed",
    ).order_by(AttendanceSession.started_at.asc()).all()
    enrollments = (
        db.query(ClassEnrollment)
        .join(Student, Student.id == ClassEnrollment.student_id)
        .filter(ClassEnrollment.class_section_id == class_section_id)
        .all()
    )
    buckets = {}
    for session in sessions:
        started = session.scheduled_start or session.started_at or session.created_at
        session_day = started.date() if started else None
        if session_day is None or (start_date and session_day < start_date) or (end_date and session_day > end_date):
            continue
        key = session_day.isoformat() if group_by == "day" else (
            session_day.strftime("%Y-%m") if group_by == "month" else session_day.strftime("%Y")
        )
        bucket = buckets.setdefault(key, {
            "period": key, "sessions": 0, "present": 0, "absent": 0,
            "total": 0, "students": {},
        })
        rows = db.query(SessionAttendance).filter(SessionAttendance.session_id == session.id).all()
        statuses = {row.user_id: row.attendance_status for row in rows}
        bucket["sessions"] += 1
        for enrollment in enrollments:
            student = enrollment.student
            user = student.user
            status = "present" if statuses.get(user.id) == "present" else "absent"
            bucket[status] += 1
            bucket["total"] += 1
            item = bucket["students"].setdefault(user.id, {
                "user_id": user.id, "roll_number": student.roll_number,
                "full_name": user.full_name, "present": 0, "absent": 0,
            })
            item[status] += 1

    groups = []
    for key in sorted(buckets):
        bucket = buckets[key]
        total = bucket["total"]
        students = []
        for item in bucket["students"].values():
            attended = item["present"] + item["absent"]
            students.append({
                **item, "sessions_attended": attended,
                "attendance_percentage": round(item["present"] * 100 / attended, 2) if attended else 0.0,
            })
        groups.append({
            "period": bucket["period"], "sessions": bucket["sessions"],
            "present": bucket["present"], "absent": bucket["absent"], "total": total,
            "attendance_percentage": round(bucket["present"] * 100 / total, 2) if total else 0.0,
            "students": sorted(students, key=lambda x: (x["roll_number"], x["full_name"])),
        })
    return {"class_section_id": class_section_id, "group_by": group_by, "groups": groups}


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    if current_user.role == "teacher" and payload.class_section_id is None:
        raise HTTPException(status_code=422, detail="Teachers must assign a class to the session")
    if payload.mode == "manual" and payload.class_section_id is None:
        raise HTTPException(status_code=422, detail="Manual attendance sessions require a class")
    if payload.class_section_id is not None:
        section = db.query(ClassSection).filter(ClassSection.id == payload.class_section_id).first()
        if section is None:
            raise HTTPException(status_code=404, detail="Class not found")
        if current_user.role == "teacher":
            teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            if not teacher or section.teacher_id != teacher.id:
                raise HTTPException(status_code=403, detail="You cannot create a session for this class")
    session = AttendanceSession(
        name=payload.name, class_section_id=payload.class_section_id,
        attendance_mode=payload.mode,
        scheduled_start=payload.scheduled_start, scheduled_end=payload.scheduled_end,
        status="draft", created_by=current_user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    audit_record(db, action="session.create", actor=current_user,
                 entity_type="session", entity_id=str(session.id), details={"name": session.name})
    return session


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    session = _get_session_or_404(db, session_id)
    _require_viewer(current_user, session, db)
    return session


@router.post("/{session_id}/start", response_model=SessionOut)
async def start_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    session = _get_session_or_404(db, session_id)
    _require_manager(current_user, session, db)
    if session.status == "active":
        raise HTTPException(status_code=409, detail="Session is already active")
    if session.status == "closed":
        raise HTTPException(status_code=409, detail="Closed sessions cannot be restarted")
    session.status = "active"
    session.started_at = now_local()
    db.commit()
    db.refresh(session)
    audit_record(db, action="session.start", actor=current_user,
                 entity_type="session", entity_id=str(session.id))
    return session


@router.post("/{session_id}/stop", response_model=SessionOut)
async def stop_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    session = _get_session_or_404(db, session_id)
    _require_manager(current_user, session, db)
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Only an active session can be stopped")
    if session.attendance_mode == "manual":
        roster_ids = {
            row[0] for row in db.query(Student.user_id)
            .join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
            .filter(ClassEnrollment.class_section_id == session.class_section_id)
            .all()
        }
        marked_ids = {
            row[0] for row in db.query(SessionAttendance.user_id)
            .filter(SessionAttendance.session_id == session_id,
                    SessionAttendance.attendance_status.in_(["present", "absent"]))
            .all()
        }
        if not roster_ids:
            raise HTTPException(status_code=409, detail="This class has no enrolled students")
        if roster_ids != marked_ids:
            raise HTTPException(
                status_code=409,
                detail=f"Mark every student present or absent before closing ({len(roster_ids - marked_ids)} unmarked)",
            )
    session.status = "closed"
    session.closed_at = now_local()
    db.commit()
    db.refresh(session)
    audit_record(db, action="session.stop", actor=current_user,
                 entity_type="session", entity_id=str(session.id))
    return session


@router.get("/{session_id}/roster")
async def get_manual_roster(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    session = _get_session_or_404(db, session_id)
    _require_manager(current_user, session, db)
    if session.attendance_mode != "manual" or session.class_section_id is None:
        raise HTTPException(status_code=409, detail="This session does not use manual class attendance")
    records = {
        row.user_id: row for row in db.query(SessionAttendance)
        .filter(SessionAttendance.session_id == session_id).all()
    }
    enrollments = (
        db.query(ClassEnrollment)
        .join(Student, Student.id == ClassEnrollment.student_id)
        .filter(ClassEnrollment.class_section_id == session.class_section_id)
        .all()
    )
    return [{
        "user_id": enrollment.student.user_id,
        "student_id": enrollment.student.id,
        "roll_number": enrollment.student.roll_number,
        "full_name": enrollment.student.user.full_name,
        "email": enrollment.student.user.email,
        "status": records.get(enrollment.student.user_id).attendance_status
            if records.get(enrollment.student.user_id) else None,
        "reason": records.get(enrollment.student.user_id).reason
            if records.get(enrollment.student.user_id) else None,
    } for enrollment in enrollments]


@router.put("/{session_id}/manual-attendance", response_model=list[DecisionOut])
async def save_manual_roster(
    session_id: int,
    payload: ManualAttendanceBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    session = _get_session_or_404(db, session_id)
    _require_manager(current_user, session, db)
    if session.attendance_mode != "manual" or session.class_section_id is None:
        raise HTTPException(status_code=409, detail="This session does not use manual class attendance")
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Manual attendance can only be changed during an active session")

    requested = [item.user_id for item in payload.entries]
    if len(requested) != len(set(requested)):
        raise HTTPException(status_code=422, detail="Each student may appear only once")
    roster_ids = {
        row[0] for row in db.query(Student.user_id)
        .join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
        .filter(ClassEnrollment.class_section_id == session.class_section_id)
        .all()
    }
    if not roster_ids or set(requested) != roster_ids:
        raise HTTPException(status_code=422, detail="Submit one present/absent mark for every enrolled student")

    results = []
    for item in payload.entries:
        record = db.query(SessionAttendance).filter(
            SessionAttendance.session_id == session_id,
            SessionAttendance.user_id == item.user_id,
        ).first()
        previous = record.attendance_status if record else None
        if record is None:
            record = SessionAttendance(session_id=session_id, user_id=item.user_id)
            db.add(record)
        record.decision = engine.MANUAL_OVERRIDE
        record.attendance_status = item.status
        record.confidence = None
        record.quality_score = None
        record.liveness_ok = None
        record.reason = payload.reason or f"Manual attendance marked {item.status}"
        record.marked_by = current_user.id
        db.flush()
        user = db.query(User).filter(User.id == item.user_id).first()
        db.add(VerificationEvent(
            session_id=session_id, user_id=item.user_id,
            user_unique_id=user.unique_id if user else None,
            event_type="manual_attendance", decision=engine.MANUAL_OVERRIDE,
            reason=f"{previous or 'unmarked'} → {item.status}: {record.reason}",
        ))
        results.append(record)
    db.commit()
    for record in results:
        db.refresh(record)
    audit_record(
        db, action="session.manual_roster", actor=current_user,
        entity_type="session", entity_id=str(session_id),
        details={"present": sum(item.status == "present" for item in payload.entries),
                 "absent": sum(item.status == "absent" for item in payload.entries)},
    )
    return [_record_out(record) for record in results]


# ── decisions ─────────────────────────────────────────────────────────────────

@router.post("/{session_id}/decisions", response_model=DecisionOut)
async def submit_decision(
    session_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    """Apply the decision engine to one verification and persist the outcome.

    This is a staff-only integration endpoint until scanner-device
    authentication is implemented. The browser monitor does not submit CV
    scores. Staff can act only within sessions they manage, and class-linked
    decisions must target an enrolled student.
    """
    session = _get_session_or_404(db, session_id)
    student = db.query(User).filter(User.id == payload.user_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    _require_manager(current_user, session, db)
    if session.class_section_id is not None and not _is_enrolled(student.id, session, db):
        raise HTTPException(status_code=403, detail="Student is not enrolled in this session's class")

    duplicate = db.query(SessionAttendance).filter(
        SessionAttendance.session_id == session_id,
        SessionAttendance.user_id == student.id,
    ).first() is not None

    decision = engine.evaluate(
        session_active=session.status == "active",
        duplicate=duplicate,
        liveness_ok=payload.liveness_ok,
        spoof_suspected=payload.spoof_suspected,
        confidence=payload.confidence,
        quality_score=payload.quality_score,
        min_confidence=settings.DECISION_MIN_CONFIDENCE,
        min_quality=settings.DECISION_MIN_QUALITY,
    )

    # For DUPLICATE we do not overwrite the original record; log the attempt.
    if decision.outcome == engine.DUPLICATE:
        original = db.query(SessionAttendance).filter(
            SessionAttendance.session_id == session_id,
            SessionAttendance.user_id == student.id,
        ).first()
        db.add(VerificationEvent(
            session_id=session_id, user_id=student.id, user_unique_id=student.unique_id,
            event_type="mark", decision=decision.outcome, confidence=payload.confidence,
            quality_score=payload.quality_score, liveness_ok=payload.liveness_ok,
            model_version=payload.model_version, threshold=decision.threshold,
            reason=decision.reason,
        ))
        db.commit()
        return _record_out(original)

    record = db.query(SessionAttendance).filter(
        SessionAttendance.session_id == session_id, SessionAttendance.user_id == student.id
    ).first()
    if record is None:
        record = SessionAttendance(
            session_id=session_id, user_id=student.id, decision=decision.outcome,
            confidence=payload.confidence, quality_score=payload.quality_score,
            liveness_ok=payload.liveness_ok, reason=decision.reason,
        )
        db.add(record)
    else:
        record.decision = decision.outcome
        record.confidence = payload.confidence
        record.quality_score = payload.quality_score
        record.liveness_ok = payload.liveness_ok
        record.reason = decision.reason
    db.flush()
    _log_event(db, record, "mark", payload.confidence, payload.quality_score,
               payload.liveness_ok, decision.threshold, decision.reason,
               current_user, payload.model_version)
    db.commit()
    db.refresh(record)
    audit_record(db, action="session.decision", actor=current_user,
                 entity_type="session", entity_id=str(session_id),
                 details={"student": student.unique_id, "outcome": decision.outcome})
    return _record_out(record)


@router.get("/{session_id}/records", response_model=list[DecisionOut])
async def list_records(
    session_id: int,
    decision_filter: Optional[str] = Query(None, alias="decision"),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    session = _get_session_or_404(db, session_id)
    _require_viewer(current_user, session, db)
    query = db.query(SessionAttendance).filter(SessionAttendance.session_id == session_id)
    if current_user.role in ("student", "user"):
        query = query.filter(SessionAttendance.user_id == current_user.id)
    if decision_filter:
        if decision_filter not in engine.OUTCOMES:
            raise HTTPException(status_code=422, detail="Unknown decision filter")
        query = query.filter(SessionAttendance.decision == decision_filter)
    records = query.order_by(SessionAttendance.marked_at.desc()).all()
    return [_record_out(r) for r in records]


@router.get("/{session_id}/events", response_model=list[EventOut])
async def list_events(
    session_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Polling feed for the live monitor (newest first)."""
    session = _get_session_or_404(db, session_id)
    _require_manager(current_user, session, db)
    return (
        db.query(VerificationEvent)
        .filter(VerificationEvent.session_id == session_id)
        .order_by(VerificationEvent.created_at.desc())
        .limit(limit).all()
    )


@router.post("/{session_id}/manual", response_model=DecisionOut)
async def manual_override(
    session_id: int,
    payload: ManualOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    session = _get_session_or_404(db, session_id)
    _require_manager(current_user, session, db)
    student = db.query(User).filter(User.id == payload.user_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    record = db.query(SessionAttendance).filter(
        SessionAttendance.session_id == session_id, SessionAttendance.user_id == student.id
    ).first()
    if record is None:
        record = SessionAttendance(session_id=session_id, user_id=student.id)
        db.add(record)
    record.decision = engine.MANUAL_OVERRIDE
    record.reason = f"Manual override ({payload.decision}): {payload.reason}"
    record.marked_by = current_user.id
    db.flush()
    _log_event(db, record, "manual", None, None, None, None, record.reason, current_user)
    db.commit()
    db.refresh(record)
    audit_record(db, action="session.manual_override", actor=current_user,
                 entity_type="session", entity_id=str(session_id),
                 details={"student": student.unique_id, "decision": payload.decision, "reason": payload.reason})
    return _record_out(record)


@router.post("/{session_id}/review/{student_id}", response_model=DecisionOut)
async def review_decision(
    session_id: int, student_id: int,
    payload: ReviewRequestManual,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
    """Resolve a REVIEW_REQUIRED record with a reasoned verdict."""
    session = _get_session_or_404(db, session_id)
    _require_manager(current_user, session, db)
    record = db.query(SessionAttendance).filter(
        SessionAttendance.session_id == session_id, SessionAttendance.user_id == student_id
    ).first()
    if record is None or record.decision != engine.REVIEW_REQUIRED:
        raise HTTPException(status_code=404, detail="No record awaiting review")
    record.decision = engine.VERIFIED if payload.decision == "VERIFIED" else engine.REJECTED
    record.reason = f"Review ({payload.decision}): {payload.reason}"
    record.marked_by = current_user.id
    db.flush()
    _log_event(db, record, "review", None, None, None, None, record.reason, current_user)
    db.commit()
    db.refresh(record)
    audit_record(db, action="session.review", actor=current_user,
                 entity_type="session", entity_id=str(session_id),
                 details={"student_id": student_id, "verdict": payload.decision, "reason": payload.reason})
    return _record_out(record)
