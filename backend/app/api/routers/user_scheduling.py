"""Current-user scheduling endpoints: shift, holidays, leave, corrections."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import extract
from sqlalchemy.orm import Session, joinedload

from app.api import deps
from app.db.session import get_db
from app.models import (
    Attendance,
    AttendanceCorrectionRequest,
    Holiday,
    LeaveRequest,
    Shift,
    User,
)
from app.schemas import CorrectionRequestCreate, LeaveRequestCreate
from app.services.audit import record as audit_record

logger = logging.getLogger("smart_attendance.user_scheduling")

router = APIRouter(prefix="/user", tags=["user-scheduling"])

# A single leave request may not span more than this (guards fat-fingered
# year-long ranges; longer planning belongs in the shift/holiday setup).
MAX_LEAVE_DAYS = 366


@router.get("/shift")
async def get_my_shift(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """The current user's assigned shift, or null when none is assigned."""
    shift: Optional[Shift] = current_user.shift
    if shift is None:
        return {"shift": None}
    return {
        "shift": {
            "id": shift.id,
            "name": shift.name,
            "start_time": shift.start_time.isoformat(),
            "end_time": shift.end_time.isoformat(),
            "grace_minutes": shift.grace_minutes,
        }
    }


@router.get("/holidays")
async def list_holidays(
    year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    query = db.query(Holiday)
    if year:
        query = query.filter(extract("year", Holiday.date) == year)
    holidays = query.order_by(Holiday.date).all()
    return [
        {"id": h.id, "date": h.date.isoformat(), "name": h.name}
        for h in holidays
    ]


def _leave_dict(req: LeaveRequest) -> dict:
    return {
        "id": req.id,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "leave_type": req.leave_type,
        "reason": req.reason,
        "status": req.status,
        "review_note": req.review_note,
        "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }


@router.post("/leave-requests")
async def create_leave_request(
    payload: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if (payload.end_date - payload.start_date).days > MAX_LEAVE_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Leave requests may span at most {MAX_LEAVE_DAYS} days.",
        )

    # Block overlapping pending/approved requests so one period cannot be
    # submitted twice or stacked on top of an already-approved absence.
    overlap = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.status.in_(["pending", "approved"]),
            LeaveRequest.start_date <= payload.end_date,
            LeaveRequest.end_date >= payload.start_date,
        )
        .first()
    )
    if overlap:
        raise HTTPException(
            status_code=409,
            detail=(
                f"You already have a {overlap.status} request covering part of "
                f"that range (#{overlap.id})."
            ),
        )

    req = LeaveRequest(
        user_id=current_user.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        leave_type=payload.leave_type,
        reason=payload.reason,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    audit_record(
        db,
        action="leave.request",
        actor=current_user,
        entity_type="leave_request",
        entity_id=str(req.id),
        details={"range": f"{req.start_date}..{req.end_date}", "type": req.leave_type},
    )
    return _leave_dict(req)


@router.get("/leave-requests")
async def list_my_leave_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    rows = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.user_id == current_user.id)
        .order_by(LeaveRequest.id.desc())
        .all()
    )
    return [_leave_dict(r) for r in rows]


def _correction_dict(req: AttendanceCorrectionRequest) -> dict:
    att = req.attendance
    return {
        "id": req.id,
        "attendance_id": req.attendance_id,
        "proposed_status": req.proposed_status,
        "proposed_time_in": req.proposed_time_in.isoformat() if req.proposed_time_in else None,
        "reason": req.reason,
        "status": req.status,
        "review_note": req.review_note,
        "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "attendance": {
            "date": att.date.isoformat(),
            "current_status": att.status,
            "current_time_in": att.time_in.isoformat() if att.time_in else None,
        }
        if att
        else None,
    }


@router.post("/correction-requests")
async def create_correction_request(
    payload: CorrectionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    attendance = (
        db.query(Attendance)
        .filter(
            Attendance.id == payload.attendance_id,
            Attendance.user_id == current_user.id,
        )
        .first()
    )
    if not attendance:
        # Do not reveal whether the record exists for someone else.
        raise HTTPException(status_code=404, detail="Attendance record not found")

    existing_pending = (
        db.query(AttendanceCorrectionRequest)
        .filter(
            AttendanceCorrectionRequest.attendance_id == attendance.id,
            AttendanceCorrectionRequest.status == "pending",
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(
            status_code=409,
            detail=f"Correction request #{existing_pending.id} is already pending for this record.",
        )

    # No-op proposals are rejected so the approval queue stays meaningful.
    if (
        payload.proposed_status == attendance.status
        and payload.proposed_time_in == attendance.time_in
    ):
        raise HTTPException(
            status_code=400,
            detail="The proposed values match the current record; nothing to correct.",
        )

    req = AttendanceCorrectionRequest(
        user_id=current_user.id,
        attendance_id=attendance.id,
        proposed_status=payload.proposed_status,
        proposed_time_in=(
            payload.proposed_time_in if payload.proposed_status == "present" else None
        ),
        reason=payload.reason.strip(),
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    audit_record(
        db,
        action="correction.request",
        actor=current_user,
        entity_type="correction_request",
        entity_id=str(req.id),
        details={
            "attendance_id": attendance.id,
            "date": str(attendance.date),
            "proposed_status": req.proposed_status,
        },
    )
    return _correction_dict(req)


@router.get("/correction-requests")
async def list_my_correction_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    rows = (
        db.query(AttendanceCorrectionRequest)
        .options(joinedload(AttendanceCorrectionRequest.attendance))
        .filter(AttendanceCorrectionRequest.user_id == current_user.id)
        .order_by(AttendanceCorrectionRequest.id.desc())
        .all()
    )
    return [_correction_dict(r) for r in rows]
