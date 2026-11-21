"""Attendance sessions + decision-engine API (AttendX Module 5/10).

All paths are versioned under /api/v1. Sessions are additive: the legacy
per-day kiosk attendance flow is unchanged. Every decision is logged as a
verification event with its inputs (never raw biometrics).
"""

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
        decision=record.decision, confidence=record.confidence,
        quality_score=record.quality_score, liveness_ok=record.liveness_ok,
        reason=record.reason, marked_at=record.marked_at,
    )


# ── session lifecycle ─────────────────────────────────────────────────────────

@router.get("", response_model=list[SessionOut])
async def list_sessions(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    return (
        db.query(AttendanceSession)
        .order_by(AttendanceSession.created_at.desc())
        .offset(skip).limit(limit).all()
    )


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_staff),
):
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
    return _get_session_or_404(db, session_id)


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
    session.status = "closed"
    session.closed_at = now_local()
    db.commit()
    db.refresh(session)
    audit_record(db, action="session.stop", actor=current_user,
                 entity_type="session", entity_id=str(session.id))
    return session


# ── decisions ─────────────────────────────────────────────────────────────────

@router.post("/{session_id}/decisions", response_model=DecisionOut)
async def submit_decision(
    session_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_optional_current_user),
):
    """Apply the decision engine to one verification and persist the outcome.

    Authenticated students may submit only their own signals; staff may submit
    for anyone. No raw frames are sent here — the kiosk first runs CV and sends
    only the resulting scores/flags.
    """
    session = _get_session_or_404(db, session_id)
    student = db.query(User).filter(User.id == payload.user_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user is not None and current_user.role == "student" and current_user.id != student.id:
        raise HTTPException(status_code=403, detail="You can only submit your own verification")

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
    _get_session_or_404(db, session_id)
    query = db.query(SessionAttendance).filter(SessionAttendance.session_id == session_id)
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
    _get_session_or_404(db, session_id)
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
