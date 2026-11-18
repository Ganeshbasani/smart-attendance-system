"""Phase 2 tests: shifts, holidays, leave, corrections, checkout, late flags."""

from datetime import date, time, timedelta

import pytest

from app.core.time_utils import today_local
from app.models import Attendance, Holiday, LeaveRequest, User
from app.services.scheduling import is_early_leave, is_late, worked_minutes

# ── Service unit tests (deterministic, no HTTP) ──────────────────────────────


class _Shift:
    """Minimal stand-in for the Shift model in pure-function tests."""

    def __init__(self, start, end, grace=0):
        self.start_time = start
        self.end_time = end
        self.grace_minutes = grace


DAY = date(2026, 6, 10)


def test_is_late_within_grace():
    shift = _Shift(time(9, 0), time(17, 0), grace=10)
    assert is_late(time(9, 5), shift, DAY) is False
    assert is_late(time(9, 10), shift, DAY) is False  # exactly at deadline
    assert is_late(time(9, 11), shift, DAY) is True


def test_is_late_without_grace():
    shift = _Shift(time(9, 0), time(17, 0), grace=0)
    assert is_late(time(9, 0), shift, DAY) is False
    assert is_late(time(9, 1), shift, DAY) is True


def test_is_late_not_applicable_without_shift_or_time():
    assert is_late(time(9, 30), None, DAY) is None
    assert is_late(None, _Shift(time(9, 0), time(17, 0)), DAY) is None
    assert is_late(time(9, 30), _Shift(time(9, 0), time(17, 0)), None) is None


def test_is_early_leave():
    shift = _Shift(time(9, 0), time(17, 0))
    assert is_early_leave(time(16, 59), shift, DAY) is True
    assert is_early_leave(time(17, 0), shift, DAY) is False
    assert is_early_leave(time(17, 30), shift, DAY) is False
    assert is_early_leave(None, shift, DAY) is None
    assert is_early_leave(time(16, 0), None, DAY) is None


def test_worked_minutes():
    assert worked_minutes(time(9, 0), time(17, 0)) == 480
    assert worked_minutes(time(9, 0), None) is None
    assert worked_minutes(None, time(17, 0)) is None
    # Checkout before check-in must not produce a negative shift.
    assert worked_minutes(time(17, 0), time(9, 0)) == 0


# ── Shifts ────────────────────────────────────────────────────────────────────


async def _create_shift(client, token, name="General", start="09:00", end="17:00", grace=15):
    resp = await client.post(
        "/admin/shifts",
        json={"name": name, "start_time": start, "end_time": end, "grace_minutes": grace},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_shift_crud_and_admin_only(client, admin_token, user_token):
    # Regular users cannot manage shifts.
    denied = await client.post(
        "/admin/shifts",
        json={"name": "X", "start_time": "09:00", "end_time": "17:00", "grace_minutes": 0},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert denied.status_code == 403

    shift = await _create_shift(client, admin_token)
    assert shift["start_time"] == "09:00:00"
    assert shift["grace_minutes"] == 15

    # Duplicate name → 409.
    dup = await client.post(
        "/admin/shifts",
        json={"name": "General", "start_time": "10:00", "end_time": "18:00", "grace_minutes": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dup.status_code == 409

    # end <= start → validation error (422).
    bad = await client.post(
        "/admin/shifts",
        json={"name": "Backwards", "start_time": "17:00", "end_time": "09:00", "grace_minutes": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert bad.status_code == 422

    updated = await client.put(
        f"/admin/shifts/{shift['id']}",
        json={"grace_minutes": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert updated.status_code == 200
    assert updated.json()["grace_minutes"] == 30

    deleted = await client.delete(
        f"/admin/shifts/{shift['id']}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_shift_assignment_and_user_shift_view(client, admin_token, user_token, db_session):
    shift = await _create_shift(client, admin_token, name="Night")
    user = db_session.query(User).filter(User.email == "user@test.com").first()
    assert user is not None

    assigned = await client.post(
        f"/admin/users/{user.unique_id}/shift-assignment",
        json={"shift_id": shift["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assigned.status_code == 200, assigned.text

    mine = await client.get(
        "/user/shift", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert mine.status_code == 200
    assert mine.json()["shift"]["name"] == "Night"
    assert mine.json()["shift"]["grace_minutes"] == 15

    # Clearing the assignment returns a null shift.
    cleared = await client.post(
        f"/admin/users/{user.unique_id}/shift-assignment",
        json={"shift_id": None},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cleared.status_code == 200
    mine2 = await client.get("/user/shift", headers={"Authorization": f"Bearer {user_token}"})
    assert mine2.json()["shift"] is None


@pytest.mark.asyncio
async def test_delete_shift_blocked_while_assigned(client, admin_token, user_token, db_session):
    shift = await _create_shift(client, admin_token, name="Stuck")
    user = db_session.query(User).filter(User.email == "user@test.com").first()
    await client.post(
        f"/admin/users/{user.unique_id}/shift-assignment",
        json={"shift_id": shift["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.delete(
        f"/admin/shifts/{shift['id']}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 409


# ── Holidays ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_holiday_crud(client, admin_token, user_token):
    day = today_local().isoformat()
    created = await client.post(
        "/admin/holidays",
        json={"date": day, "name": "Founders Day"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert created.status_code == 200, created.text

    dup = await client.post(
        "/admin/holidays",
        json={"date": day, "name": "Other"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dup.status_code == 409

    # Regular users can view but not create.
    view = await client.get("/user/holidays", headers={"Authorization": f"Bearer {user_token}"})
    assert view.status_code == 200
    assert any(h["date"] == day for h in view.json())
    denied = await client.post(
        "/admin/holidays",
        json={"date": "2030-01-01", "name": "Nope"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert denied.status_code == 403

    holiday_id = created.json()["id"]
    deleted = await client.delete(
        f"/admin/holidays/{holiday_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_mark_absent_skips_holidays(client, admin_token, db_session):
    day = today_local()
    db_session.add(Holiday(date=day, name="Test Holiday"))
    db_session.commit()

    resp = await client.post(
        "/admin/mark-absent", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["skipped_holiday"] is True
    assert body["absent_count"] == 0

    rows = db_session.query(Attendance).filter(Attendance.date == day).all()
    db_session.expire_all()
    assert db_session.query(Attendance).filter(Attendance.date == day).count() == 0
    assert rows == []


# ── Late flags via admin marking ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_present_computes_late_flag(client, admin_token, user_token, db_session):
    shift = await _create_shift(client, admin_token, name="Office", start="09:00", end="17:00", grace=10)
    user = db_session.query(User).filter(User.email == "user@test.com").first()
    await client.post(
        f"/admin/users/{user.unique_id}/shift-assignment",
        json={"shift_id": shift["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # 09:30 is past 09:00 + 10 min grace → late.
    late = await client.post(
        f"/admin/attendance/mark-present/{user.unique_id}",
        data={"time_in": "09:30"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert late.status_code == 200, late.text
    assert late.json()["attendance"]["is_late"] is True

    # Correcting to 09:05 (within grace) must clear the flag.
    record_id = late.json()["attendance"]["id"]
    fixed = await client.put(
        f"/admin/attendance/{record_id}",
        data={"status": "present", "time_in": "09:05"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["attendance"]["is_late"] is False

    # Marking absent clears time and flags.
    cleared = await client.put(
        f"/admin/attendance/{record_id}",
        data={"status": "absent"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cleared.status_code == 200
    att = cleared.json()["attendance"]
    assert att["time_in"] is None
    assert att["is_late"] is None
    assert att["is_early_leave"] is None


# ── Checkout ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_flow(client, admin_token, user_token, db_session):
    user = db_session.query(User).filter(User.email == "user@test.com").first()
    today = today_local()
    record = Attendance(user_id=user.id, date=today, time_in=time(9, 0), status="present")
    db_session.add(record)
    db_session.commit()

    # Checkout without a session is rejected.
    anon = await client.post("/attendance/checkout")
    assert anon.status_code in (401, 403)

    resp = await client.post(
        "/attendance/checkout", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["attendance"]
    assert body["time_out"] is not None
    assert body["worked_minutes"] is not None and body["worked_minutes"] >= 0

    # Second checkout of the same day is rejected.
    again = await client.post(
        "/attendance/checkout", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_checkout_requires_checkin(client, user_token):
    resp = await client.post(
        "/attendance/checkout", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert resp.status_code == 400
    assert "check-in" in resp.json()["detail"].lower()


# ── Leave workflow ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_leave_request_lifecycle(client, admin_token, user_token, db_session):
    today = today_local()
    payload = {
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=1)).isoformat(),
        "leave_type": "sick",
        "reason": "Flu",
    }
    created = await client.post(
        "/user/leave-requests", json=payload, headers={"Authorization": f"Bearer {user_token}"}
    )
    assert created.status_code == 200, created.text
    req_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    # Overlapping pending request → 409.
    overlap = await client.post(
        "/user/leave-requests", json=payload, headers={"Authorization": f"Bearer {user_token}"}
    )
    assert overlap.status_code == 409

    # Invalid range → 422 (schema validator).
    bad = await client.post(
        "/user/leave-requests",
        json={"start_date": today.isoformat(), "end_date": (today - timedelta(days=1)).isoformat()},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert bad.status_code == 422

    # Reject without a note is refused.
    no_note = await client.post(
        f"/admin/leave-requests/{req_id}/reject",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert no_note.status_code == 400

    # Approve.
    approved = await client.post(
        f"/admin/leave-requests/{req_id}/approve",
        json={"note": "Enjoy"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    # Deciding twice → 400.
    again = await client.post(
        f"/admin/leave-requests/{req_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert again.status_code == 400

    # Regular users cannot review.
    denied = await client.post(
        f"/admin/leave-requests/{req_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_mark_absent_skips_approved_leave(client, admin_token, user_token, db_session):
    # Three users exist after fixtures: admin + user (gets leave) — mark-absent
    # must create an absent row for the admin but not for the user on leave.
    today = today_local()
    user = db_session.query(User).filter(User.email == "user@test.com").first()
    db_session.add(
        LeaveRequest(
            user_id=user.id,
            start_date=today,
            end_date=today,
            leave_type="annual",
            status="approved",
        )
    )
    db_session.commit()

    resp = await client.post(
        "/admin/mark-absent", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["skipped_leave"] == 1
    assert body["absent_count"] >= 1

    db_session.expire_all()
    absent_user_ids = {
        r[0]
        for r in db_session.query(Attendance.user_id)
        .filter(Attendance.date == today, Attendance.status == "absent")
        .all()
    }
    assert user.id not in absent_user_ids, "user on approved leave must not be marked absent"
    admin = db_session.query(User).filter(User.email == "admin@test.com").first()
    assert admin.id in absent_user_ids


# ── Correction workflow ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_correction_request_lifecycle(client, admin_token, user_token, db_session):
    user = db_session.query(User).filter(User.email == "user@test.com").first()
    today = today_local()
    record = Attendance(user_id=user.id, date=today, time_in=time(9, 0), status="present")
    db_session.add(record)
    db_session.commit()
    record_id = record.id

    # No-op proposal → 400.
    noop = await client.post(
        "/user/correction-requests",
        json={
            "attendance_id": record_id,
            "proposed_status": "present",
            "proposed_time_in": "09:00",
            "reason": "same",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert noop.status_code == 400

    created = await client.post(
        "/user/correction-requests",
        json={
            "attendance_id": record_id,
            "proposed_status": "present",
            "proposed_time_in": "08:30",
            "reason": "Clock at the gate was broken",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert created.status_code == 200, created.text
    req_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    # Duplicate pending → 409.
    dup = await client.post(
        "/user/correction-requests",
        json={
            "attendance_id": record_id,
            "proposed_status": "absent",
            "reason": "again",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert dup.status_code == 409

    # Admin sees it pending and approves → attendance row updated.
    pending = await client.get(
        "/admin/correction-requests",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert pending.status_code == 200
    assert any(r["id"] == req_id for r in pending.json())

    approved = await client.post(
        f"/admin/correction-requests/{req_id}/approve",
        json={"note": "Verified with guard"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    db_session.expire_all()
    updated = db_session.get(Attendance, record_id)
    assert updated.time_in == time(8, 30)

    # Second decision → 400.
    again = await client.post(
        f"/admin/correction-requests/{req_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_correction_reject_requires_note_and_preserves_record(
    client, admin_token, user_token, db_session
):
    user = db_session.query(User).filter(User.email == "user@test.com").first()
    today = today_local()
    record = Attendance(user_id=user.id, date=today, time_in=time(9, 0), status="present")
    db_session.add(record)
    db_session.commit()

    created = await client.post(
        "/user/correction-requests",
        json={
            "attendance_id": record.id,
            "proposed_status": "absent",
            "reason": "I was not there",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert created.status_code == 200, created.text
    req_id = created.json()["id"]

    no_note = await client.post(
        f"/admin/correction-requests/{req_id}/reject",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert no_note.status_code == 400

    rejected = await client.post(
        f"/admin/correction-requests/{req_id}/reject",
        json={"note": "Badge logs show entry"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    db_session.expire_all()
    unchanged = db_session.get(Attendance, record.id)
    assert unchanged.status == "present"
    assert unchanged.time_in == time(9, 0)


@pytest.mark.asyncio
async def test_correction_cannot_touch_other_users_record(
    client, admin_token, user_token, db_session
):
    # The admin's attendance row, corrected by the regular user → 404.
    admin = db_session.query(User).filter(User.email == "admin@test.com").first()
    record = Attendance(
        user_id=admin.id, date=today_local(), time_in=time(9, 0), status="present"
    )
    db_session.add(record)
    db_session.commit()

    resp = await client.post(
        "/user/correction-requests",
        json={
            "attendance_id": record.id,
            "proposed_status": "absent",
            "reason": "sneaky",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404
