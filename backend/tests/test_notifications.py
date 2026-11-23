"""Phase 4 tests: notification rows, user scoping, mark-read, event wiring."""

from datetime import time, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.core.time_utils import today_local
from app.models import Attendance, Notification, User
from app.services.notifications import notify


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _add_notification(db, user_id, title, message="m", is_read=False, type_="info"):
    row = Notification(
        user_id=user_id, type=type_, title=title, message=message, is_read=is_read
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _get_user(db, email):
    user = db.query(User).filter(User.email == email).first()
    assert user is not None, f"{email} not found"
    return user


# ── Scoping / read state ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_is_scoped_to_current_user(client, admin_token, user_token, db_session):
    admin = _get_user(db_session, "admin@test.com")
    user = _get_user(db_session, "user@test.com")
    _add_notification(db_session, admin.id, "Admin only")
    mine = _add_notification(db_session, user.id, "User only")

    resp = await client.get("/notifications", headers=_auth(user_token))
    assert resp.status_code == 200, resp.text
    titles = [n["title"] for n in resp.json()]
    assert titles == ["User only"], "another user's notification must never be listed"
    assert resp.headers["X-Total-Count"] == "1"

    # The admin sees only their own row.
    as_admin = await client.get("/notifications", headers=_auth(admin_token))
    assert [n["title"] for n in as_admin.json()] == ["Admin only"]
    assert all(n["id"] != mine.id for n in as_admin.json())


@pytest.mark.asyncio
async def test_list_filters_and_pagination(client, user_token, db_session):
    user = _get_user(db_session, "user@test.com")
    _add_notification(db_session, user.id, "Unread A")
    _add_notification(db_session, user.id, "Unread B")
    _add_notification(db_session, user.id, "Read C", is_read=True)

    page = await client.get(
        "/notifications", params={"limit": 1}, headers=_auth(user_token)
    )
    assert page.status_code == 200
    assert len(page.json()) == 1
    assert page.headers["X-Total-Count"] == "3"

    unread = await client.get(
        "/notifications", params={"unread_only": "true"}, headers=_auth(user_token)
    )
    assert unread.status_code == 200
    assert {n["title"] for n in unread.json()} == {"Unread A", "Unread B"}
    assert unread.headers["X-Total-Count"] == "2"

    # limit is validated (ge=1).
    bad = await client.get("/notifications", params={"limit": 0}, headers=_auth(user_token))
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_unread_count_and_read_all(client, user_token, db_session):
    user = _get_user(db_session, "user@test.com")
    _add_notification(db_session, user.id, "U1")
    _add_notification(db_session, user.id, "U2")
    _add_notification(db_session, user.id, "R1", is_read=True)

    count = await client.get("/notifications/unread-count", headers=_auth(user_token))
    assert count.status_code == 200
    assert count.json() == {"count": 2}

    read_all = await client.post("/notifications/read-all", headers=_auth(user_token))
    assert read_all.status_code == 200
    assert read_all.json() == {"updated": 2}

    count2 = await client.get("/notifications/unread-count", headers=_auth(user_token))
    assert count2.json() == {"count": 0}

    # Idempotent: a second run has nothing left to update.
    again = await client.post("/notifications/read-all", headers=_auth(user_token))
    assert again.json() == {"updated": 0}


@pytest.mark.asyncio
async def test_mark_read_owner_scoping_and_404(client, admin_token, user_token, db_session):
    admin = _get_user(db_session, "admin@test.com")
    row = _add_notification(db_session, admin.id, "Private")

    # Another user gets 404 (not 403) so ids cannot be probed.
    foreign = await client.post(f"/notifications/{row.id}/read", headers=_auth(user_token))
    assert foreign.status_code == 404

    # Nonexistent id is also 404.
    missing = await client.post("/notifications/999999/read", headers=_auth(user_token))
    assert missing.status_code == 404

    # The owner can mark it read; a repeat call is a harmless no-op.
    owner = await client.post(f"/notifications/{row.id}/read", headers=_auth(admin_token))
    assert owner.status_code == 200
    assert owner.json()["is_read"] is True
    assert owner.json()["read_at"] is not None
    repeat = await client.post(f"/notifications/{row.id}/read", headers=_auth(admin_token))
    assert repeat.status_code == 200
    assert repeat.json()["is_read"] is True


@pytest.mark.asyncio
async def test_notifications_require_auth(client):
    for method, path in (
        ("get", "/notifications"),
        ("get", "/notifications/unread-count"),
        ("post", "/notifications/read-all"),
        ("post", "/notifications/1/read"),
    ):
        resp = await getattr(client, method)(path)
        assert resp.status_code in (401, 403), f"{method} {path} was open"


# ── Event wiring: decisions reach the affected user ──────────────────────────


@pytest.mark.asyncio
async def test_leave_approval_notifies_applicant(client, admin_token, user_token, db_session):
    today = today_local()
    created = await client.post(
        "/user/leave-requests",
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
            "leave_type": "sick",
            "reason": "Flu",
        },
        headers=_auth(user_token),
    )
    assert created.status_code == 200, created.text
    req_id = created.json()["id"]

    approved = await client.post(
        f"/admin/leave-requests/{req_id}/approve",
        json={"note": "Enjoy the rest"},
        headers=_auth(admin_token),
    )
    assert approved.status_code == 200, approved.text

    resp = await client.get("/notifications", headers=_auth(user_token))
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1, f"expected exactly one notification, got {items}"
    n = items[0]
    assert n["type"] == "leave_decision"
    assert n["is_read"] is False
    assert "approved" in n["title"].lower()
    assert "Enjoy the rest" in n["message"], "reviewer note must reach the applicant"
    assert n["entity_type"] == "leave_request"
    assert n["entity_id"] == str(req_id)
    assert n["created_at"] is not None

    # The reviewer (admin) is not notified about their own decision.
    as_admin = await client.get("/notifications", headers=_auth(admin_token))
    assert as_admin.json() == []


@pytest.mark.asyncio
async def test_leave_rejection_notifies_with_required_note(
    client, admin_token, user_token, db_session
):
    today = today_local()
    created = await client.post(
        "/user/leave-requests",
        json={
            "start_date": (today + timedelta(days=10)).isoformat(),
            "end_date": (today + timedelta(days=11)).isoformat(),
            "leave_type": "annual",
            "reason": "Trip",
        },
        headers=_auth(user_token),
    )
    assert created.status_code == 200, created.text
    req_id = created.json()["id"]

    rejected = await client.post(
        f"/admin/leave-requests/{req_id}/reject",
        json={"note": "Peak delivery week"},
        headers=_auth(admin_token),
    )
    assert rejected.status_code == 200, rejected.text

    resp = await client.get("/notifications", headers=_auth(user_token))
    n = resp.json()[0]
    assert n["type"] == "leave_decision"
    assert "rejected" in n["title"].lower()
    assert "Peak delivery week" in n["message"]


@pytest.mark.asyncio
async def test_correction_decision_notifies_applicant(client, admin_token, user_token, db_session):
    user = _get_user(db_session, "user@test.com")
    today = today_local()
    record = Attendance(user_id=user.id, date=today, time_in=time(9, 0), status="present")
    db_session.add(record)
    db_session.commit()

    created = await client.post(
        "/user/correction-requests",
        json={
            "attendance_id": record.id,
            "proposed_status": "present",
            "proposed_time_in": "08:30",
            "reason": "Gate clock broken",
        },
        headers=_auth(user_token),
    )
    assert created.status_code == 200, created.text
    req_id = created.json()["id"]

    approved = await client.post(
        f"/admin/correction-requests/{req_id}/approve",
        json={"note": "Checked with security"},
        headers=_auth(admin_token),
    )
    assert approved.status_code == 200, approved.text

    resp = await client.get("/notifications", headers=_auth(user_token))
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1, f"expected exactly one notification, got {items}"
    n = items[0]
    assert n["type"] == "correction_decision"
    assert "approved" in n["title"].lower()
    assert str(today) in n["message"]
    assert "Checked with security" in n["message"]
    assert n["entity_type"] == "correction_request"
    assert n["entity_id"] == str(req_id)


@pytest.mark.asyncio
async def test_shift_assignment_notifies_only_on_change(client, admin_token, user_token, db_session):
    user = _get_user(db_session, "user@test.com")
    shift = await client.post(
        "/admin/shifts",
        json={"name": "Late", "start_time": "13:00", "end_time": "21:00", "grace_minutes": 10},
        headers=_auth(admin_token),
    )
    assert shift.status_code == 200, shift.text
    shift_id = shift.json()["id"]

    assigned = await client.post(
        f"/admin/users/{user.unique_id}/shift-assignment",
        json={"shift_id": shift_id},
        headers=_auth(admin_token),
    )
    assert assigned.status_code == 200, assigned.text

    resp = await client.get("/notifications", headers=_auth(user_token))
    items = resp.json()
    assert len(items) == 1, f"expected one notification after assign, got {len(items)}"
    assert items[0]["type"] == "shift_assigned"
    assert "Late" in items[0]["message"]
    assert "13:00" in items[0]["message"]
    assert "21:00" in items[0]["message"]

    # Re-assigning the identical shift is not a change → no extra notification.
    await client.post(
        f"/admin/users/{user.unique_id}/shift-assignment",
        json={"shift_id": shift_id},
        headers=_auth(admin_token),
    )
    resp2 = await client.get("/notifications", headers=_auth(user_token))
    assert len(resp2.json()) == 1

    # Clearing produces a second, distinct notification.
    cleared = await client.post(
        f"/admin/users/{user.unique_id}/shift-assignment",
        json={"shift_id": None},
        headers=_auth(admin_token),
    )
    assert cleared.status_code == 200, cleared.text
    resp3 = await client.get("/notifications", headers=_auth(user_token))
    items3 = resp3.json()
    assert len(items3) == 2
    assert items3[0]["type"] == "shift_cleared"
    assert "cleared" in items3[0]["message"].lower()


# ── Service behaviour: kill switches, email channel, failure isolation ───────


@pytest.mark.asyncio
async def test_disabled_flag_writes_no_row(client, admin_token, user_token, db_session, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATIONS_ENABLED", False)
    today = today_local()
    created = await client.post(
        "/user/leave-requests",
        json={
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
            "leave_type": "sick",
            "reason": "Flu",
        },
        headers=_auth(user_token),
    )
    assert created.status_code == 200, created.text
    approved = await client.post(
        f"/admin/leave-requests/{created.json()['id']}/approve",
        json={},
        headers=_auth(admin_token),
    )
    assert approved.status_code == 200, approved.text

    resp = await client.get("/notifications", headers=_auth(user_token))
    assert resp.json() == []
    count = await client.get("/notifications/unread-count", headers=_auth(user_token))
    assert count.json() == {"count": 0}


@pytest.mark.asyncio
async def test_email_channel_off_by_default(client, user_token, db_session):
    assert settings.EMAIL_NOTIFY_ENABLED is False, "email must default to off"
    user = _get_user(db_session, "user@test.com")
    with patch("app.services.notifications.smtplib.SMTP") as smtp_cls:
        notify(
            db_session,
            user_id=user.id,
            type="info",
            title="Hello",
            message="World",
            email_to=user.email,
        )
        smtp_cls.assert_not_called(), "SMTP must not be dialled when email is off"
    row = db_session.query(Notification).filter(Notification.user_id == user.id).one()
    assert row.title == "Hello", "the in-app row is written regardless of email"


@pytest.mark.asyncio
async def test_email_copy_sent_when_enabled(
    client, admin_token, user_token, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "EMAIL_NOTIFY_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "notify@test.com")

    today = today_local()
    created = await client.post(
        "/user/leave-requests",
        json={
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
            "leave_type": "annual",
            "reason": "Rest",
        },
        headers=_auth(user_token),
    )
    req_id = created.json()["id"]

    with patch("app.services.notifications.smtplib.SMTP") as smtp_cls:
        smtp = smtp_cls.return_value.__enter__.return_value
        approved = await client.post(
            f"/admin/leave-requests/{req_id}/approve",
            json={"note": "Approved by mail test"},
            headers=_auth(admin_token),
        )
        assert approved.status_code == 200, approved.text
        smtp_cls.assert_called_once()
        smtp.send_message.assert_called_once()

    msg = smtp.send_message.call_args[0][0]
    assert msg["To"] == "user@test.com"
    assert "Approved by mail test" in msg.get_content()

    # The in-app row exists independently of the email.
    resp = await client.get("/notifications", headers=_auth(user_token))
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_smtp_failure_never_fails_the_request(
    client, admin_token, user_token, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "EMAIL_NOTIFY_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "notify@test.com")

    today = today_local()
    created = await client.post(
        "/user/leave-requests",
        json={
            "start_date": (today + timedelta(days=20)).isoformat(),
            "end_date": (today + timedelta(days=20)).isoformat(),
            "leave_type": "annual",
            "reason": "Trip",
        },
        headers=_auth(user_token),
    )
    req_id = created.json()["id"]

    with patch(
        "app.services.notifications.smtplib.SMTP", side_effect=OSError("connection refused")
    ):
        approved = await client.post(
            f"/admin/leave-requests/{req_id}/approve",
            json={},
            headers=_auth(admin_token),
        )
    # The approval itself must not depend on the mail server.
    assert approved.status_code == 200, approved.text

    resp = await client.get("/notifications", headers=_auth(user_token))
    assert len(resp.json()) == 1, "in-app row must survive an SMTP outage"


def test_notify_never_raises_when_persistence_fails():
    assert settings.NOTIFICATIONS_ENABLED is True, "test assumes notifications are on"
    broken = MagicMock()
    broken.add.side_effect = RuntimeError("database is locked")

    # Must not raise.
    notify(broken, user_id=1, type="info", title="T", message="M")

    broken.rollback.assert_called_once()
