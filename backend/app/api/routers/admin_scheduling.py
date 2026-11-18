"""Admin endpoints: shifts, holidays, leave review, attendance corrections."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import extract, func
from sqlalchemy.orm import Session, joinedload

from app.api import deps
from app.core.time_utils import utc_now_naive
from app.db.session import get_db
from app.models import (
    Attendance,
    AttendanceCorrectionRequest,
    Holiday,
    LeaveRequest,
    Shift,
    User,
)
from app.schemas import (
    HolidayCreate,
    ReviewRequest,
    ShiftAssignment,
    ShiftCreate,
    ShiftUpdate,
)
from app.services.audit import record as audit_record
from app.services.scheduling import is_late

logger = logging.getLogger("smart_attendance.admin_scheduling")

router = APIRouter(prefix="/admin", tags=["admin-scheduling"])


# ── Shifts ────────────────────────────────────────────────────────────────────

def _shift_dict(shift: Shift, user_count: int = 0) -> dict:
    return {
        "id": shift.id,
        "name": shift.name,
        "start_time": shift.start_time.isoformat(),
        "end_time": shift.end_time.isoformat(),
        "grace_minutes": shift.grace_minutes,
        "is_active": shift.is_active,
        "assigned_users": user_count,
    }


@router.get("/shifts")
async def list_shifts(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    counts = dict(
        db.query(User.shift_id, func.count(User.id))
        .filter(User.shift_id.isnot(None))
        .group_by(User.shift_id)
        .all()
    )
    shifts = db.query(Shift).order_by(Shift.name).all()
    return [_shift_dict(s, counts.get(s.id, 0)) for s in shifts]


@router.post("/shifts")
async def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    if db.query(Shift).filter(Shift.name == payload.name).first():
        raise HTTPException(status_code=409, detail="A shift with that name already exists")
    shift = Shift(
        name=payload.name,
        start_time=payload.start_time,
        end_time=payload.end_time,
        grace_minutes=payload.grace_minutes,
        is_active=True,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    audit_record(
        db,
        action="shift.create",
        actor=current_user,
        entity_type="shift",
        entity_id=str(shift.id),
        details={"name": shift.name, "start": str(shift.start_time), "end": str(shift.end_time)},
    )
    return _shift_dict(shift)


@router.put("/shifts/{shift_id}")
async def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if payload.name is not None and payload.name != shift.name:
        if db.query(Shift).filter(Shift.name == payload.name, Shift.id != shift_id).first():
            raise HTTPException(status_code=409, detail="A shift with that name already exists")
        shift.name = payload.name
    if payload.start_time is not None:
        shift.start_time = payload.start_time
    if payload.end_time is not None:
        shift.end_time = payload.end_time
    # Guard against an update that only moves one side of the window.
    if shift.end_time <= shift.start_time:
        raise HTTPException(status_code=400, detail="end_time must be later than start_time")
    if payload.grace_minutes is not None:
        shift.grace_minutes = payload.grace_minutes
    if payload.is_active is not None:
        shift.is_active = payload.is_active

    db.commit()
    db.refresh(shift)
    audit_record(
        db,
        action="shift.update",
        actor=current_user,
        entity_type="shift",
        entity_id=str(shift.id),
        details={"name": shift.name, "is_active": shift.is_active},
    )
    return _shift_dict(shift)


@router.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    assigned = db.query(func.count(User.id)).filter(User.shift_id == shift_id).scalar() or 0
    if assigned:
        raise HTTPException(
            status_code=409,
            detail=f"Shift is assigned to {assigned} user(s). Reassign them first.",
        )
    db.delete(shift)
    db.commit()
    audit_record(
        db,
        action="shift.delete",
        actor=current_user,
        entity_type="shift",
        entity_id=str(shift_id),
    )
    return {"message": f"Shift {shift_id} deleted"}


@router.post("/users/{user_id}/shift-assignment")
async def assign_user_shift(
    user_id: str,
    payload: ShiftAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    user = db.query(User).filter(User.unique_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.shift_id is not None:
        shift = db.query(Shift).filter(Shift.id == payload.shift_id).first()
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found")

    previous = user.shift_id
    user.shift_id = payload.shift_id
    db.commit()
    audit_record(
        db,
        action="shift.assign",
        actor=current_user,
        entity_type="user",
        entity_id=user_id,
        details={"from_shift": previous, "to_shift": payload.shift_id},
    )
    return {
        "message": "Shift assigned" if payload.shift_id else "Shift cleared",
        "user_id": user_id,
        "shift_id": payload.shift_id,
    }


# ── Holidays ──────────────────────────────────────────────────────────────────

@router.get("/holidays")
async def list_holidays(
    year: int = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    query = db.query(Holiday)
    if year:
        query = query.filter(extract("year", Holiday.date) == year)
    holidays = query.order_by(Holiday.date).all()
    return [
        {"id": h.id, "date": h.date.isoformat(), "name": h.name}
        for h in holidays
    ]


@router.post("/holidays")
async def create_holiday(
    payload: HolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    if db.query(Holiday).filter(Holiday.date == payload.date).first():
        raise HTTPException(status_code=409, detail="A holiday already exists on that date")
    holiday = Holiday(date=payload.date, name=payload.name)
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    audit_record(
        db,
        action="holiday.create",
        actor=current_user,
        entity_type="holiday",
        entity_id=str(holiday.id),
        details={"date": str(holiday.date), "name": holiday.name},
    )
    return {"id": holiday.id, "date": holiday.date.isoformat(), "name": holiday.name}


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(holiday)
    db.commit()
    audit_record(
        db,
        action="holiday.delete",
        actor=current_user,
        entity_type="holiday",
        entity_id=str(holiday_id),
        details={"date": str(holiday.date), "name": holiday.name},
    )
    return {"message": "Holiday deleted"}


# ── Leave requests ────────────────────────────────────────────────────────────

def _leave_dict(req: LeaveRequest, user: Optional[User] = None) -> dict:
    data = {
        "id": req.id,
        "user_id": req.user_id,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "leave_type": req.leave_type,
        "reason": req.reason,
        "status": req.status,
        "review_note": req.review_note,
        "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }
    if user is not None:
        data["user"] = {
            "unique_id": user.unique_id,
            "full_name": user.full_name,
            "email": user.email,
            "department": user.department,
        }
    return data


@router.get("/leave-requests")
async def list_leave_requests(
    response: Response,
    status: str = Query(None, pattern="^(pending|approved|rejected)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    query = db.query(LeaveRequest).options(joinedload(LeaveRequest.user))
    if status:
        query = query.filter(LeaveRequest.status == status)
    total = query.count()
    rows = (
        query.order_by(LeaveRequest.id.desc()).offset(offset).limit(limit).all()
    )
    # joinedload above means no per-row lazy load.
    result = []
    for req in rows:
        result.append(_leave_dict(req, req.user))
    response.headers["X-Total-Count"] = str(total)
    return result


async def _review_leave(
    request_id: int,
    decision: str,
    body: ReviewRequest,
    admin: User,
    db: Session,
):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {req.status}")
    if decision == "rejected" and not (body.note and body.note.strip()):
        raise HTTPException(status_code=400, detail="A note is required when rejecting")

    req.status = decision
    req.review_note = body.note.strip() if body.note else None
    req.reviewed_by = admin.id
    req.reviewed_at = utc_now_naive()
    db.commit()
    db.refresh(req)
    audit_record(
        db,
        action="leave.review",
        actor=admin,
        entity_type="leave_request",
        entity_id=str(req.id),
        details={
            "decision": decision,
            "applicant": req.user.unique_id if req.user else None,
            "range": f"{req.start_date}..{req.end_date}",
        },
    )
    return _leave_dict(req, req.user)


@router.post("/leave-requests/{request_id}/approve")
async def approve_leave_request(
    request_id: int,
    body: ReviewRequest = ReviewRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    return await _review_leave(request_id, "approved", body, current_user, db)


@router.post("/leave-requests/{request_id}/reject")
async def reject_leave_request(
    request_id: int,
    body: ReviewRequest = ReviewRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    return await _review_leave(request_id, "rejected", body, current_user, db)


# ── Attendance correction requests ────────────────────────────────────────────

def _correction_dict(req: AttendanceCorrectionRequest) -> dict:
    att = req.attendance
    return {
        "id": req.id,
        "user_id": req.user_id,
        "attendance_id": req.attendance_id,
        "proposed_status": req.proposed_status,
        "proposed_time_in": req.proposed_time_in.isoformat() if req.proposed_time_in else None,
        "reason": req.reason,
        "status": req.status,
        "review_note": req.review_note,
        "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "user": {
            "unique_id": req.user.unique_id,
            "full_name": req.user.full_name,
            "email": req.user.email,
            "department": req.user.department,
        }
        if req.user
        else None,
        "attendance": {
            "date": att.date.isoformat(),
            "current_status": att.status,
            "current_time_in": att.time_in.isoformat() if att.time_in else None,
        }
        if att
        else None,
    }


@router.get("/correction-requests")
async def list_correction_requests(
    response: Response,
    status: str = Query(None, pattern="^(pending|approved|rejected)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    query = db.query(AttendanceCorrectionRequest).options(
        joinedload(AttendanceCorrectionRequest.user),
        joinedload(AttendanceCorrectionRequest.attendance),
    )
    if status:
        query = query.filter(AttendanceCorrectionRequest.status == status)
    total = query.count()
    rows = (
        query.order_by(AttendanceCorrectionRequest.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    response.headers["X-Total-Count"] = str(total)
    return [_correction_dict(r) for r in rows]


@router.post("/correction-requests/{request_id}/approve")
async def approve_correction_request(
    request_id: int,
    body: ReviewRequest = ReviewRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    return await _review_correction(request_id, "approved", body, current_user, db)


@router.post("/correction-requests/{request_id}/reject")
async def reject_correction_request(
    request_id: int,
    body: ReviewRequest = ReviewRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    return await _review_correction(request_id, "rejected", body, current_user, db)


async def _review_correction(
    request_id: int,
    decision: str,
    body: ReviewRequest,
    admin: User,
    db: Session,
):
    req = (
        db.query(AttendanceCorrectionRequest)
        .filter(AttendanceCorrectionRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Correction request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {req.status}")
    if decision == "rejected" and not (body.note and body.note.strip()):
        raise HTTPException(status_code=400, detail="A note is required when rejecting")

    attendance = db.query(Attendance).filter(Attendance.id == req.attendance_id).first()
    if attendance is None:
        raise HTTPException(status_code=409, detail="The attendance record no longer exists")

    previous_status, previous_time = attendance.status, attendance.time_in
    if decision == "approved":
        attendance.status = req.proposed_status
        attendance.time_in = (
            req.proposed_time_in if req.proposed_status == "present" else None
        )
        # Re-derive lateness from the user's shift for the corrected arrival.
        attendance.is_late = is_late(
            attendance.time_in, req.user.shift if req.user else None, attendance.date
        )
        if attendance.status == "absent":
            attendance.time_out = None
            attendance.is_early_leave = None

    req.status = decision
    req.review_note = body.note.strip() if body.note else None
    req.reviewed_by = admin.id
    req.reviewed_at = utc_now_naive()
    db.commit()
    db.refresh(req)
    audit_record(
        db,
        action="correction.review",
        actor=admin,
        entity_type="correction_request",
        entity_id=str(req.id),
        details={
            "decision": decision,
            "applicant": req.user.unique_id if req.user else None,
            "attendance_id": req.attendance_id,
            "from_status": previous_status,
            "to_status": attendance.status if decision == "approved" else previous_status,
            "from_time_in": str(previous_time) if previous_time else None,
        },
    )
    return _correction_dict(req)
