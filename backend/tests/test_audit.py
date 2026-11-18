"""Audit logging tests: writes, admin-only read API, and filters."""

import pytest

from app.models import AuditLog, Attendance, User
from tests.conftest import register_user


@pytest.mark.asyncio
async def test_register_and_login_are_audited(client, db_session):
    await register_user(client, "audited@test.com", "AuditedPass1!", "Audited User")
    await client.post(
        "/auth/login", json={"email": "audited@test.com", "password": "AuditedPass1!"}
    )

    actions = [
        row.action
        for row in db_session.query(AuditLog).order_by(AuditLog.id).all()
    ]
    assert "auth.register" in actions
    assert "auth.login" in actions

    login_row = (
        db_session.query(AuditLog).filter(AuditLog.action == "auth.login").first()
    )
    assert login_row.actor_email == "audited@test.com"


@pytest.mark.asyncio
async def test_audit_does_not_leak_into_api_responses(client):
    """The login/register response shape must be unchanged by audit logging."""
    resp = await client.post(
        "/auth/register",
        json={"email": "shape@test.com", "password": "ShapePass1!", "full_name": "S"},
    )
    body = resp.json()
    assert set(body.keys()) == {"access_token", "token_type", "user"}


@pytest.mark.asyncio
async def test_audit_logs_endpoint_requires_admin(client, user_token):
    resp = await client.get(
        "/admin/audit-logs", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_endpoint_requires_auth(client):
    # HTTPBearer returns 403 when no credentials are supplied on this FastAPI
    # version; either way the endpoint must reject anonymous callers.
    resp = await client.get("/admin/audit-logs")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_audit_logs_lists_and_counts(client, admin_token):
    resp = await client.get(
        "/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200, resp.text
    entries = resp.json()
    assert len(entries) >= 1
    # The admin's own registration/login must appear.
    actions = {e["action"] for e in entries}
    assert "auth.register" in actions
    assert int(resp.headers["X-Total-Count"]) >= len(entries)
    # Newest first.
    ids = [e["id"] for e in entries]
    assert ids == sorted(ids, reverse=True)


@pytest.mark.asyncio
async def test_audit_logs_action_filter(client, admin_token):
    # admin_token only registers; log in once so an auth.login row exists.
    login = await client.post(
        "/auth/login", json={"email": "admin@test.com", "password": "AdminPass1!"}
    )
    assert login.status_code == 200, login.text

    resp = await client.get(
        "/admin/audit-logs",
        params={"action": "auth.login"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert entries, "expected at least one auth.login entry"
    assert all(e["action"] == "auth.login" for e in entries)


@pytest.mark.asyncio
async def test_audit_logs_pagination(client, admin_token):
    resp = await client.get(
        "/admin/audit-logs",
        params={"limit": 1, "offset": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) <= 1
    assert int(resp.headers["X-Total-Count"]) >= 1


@pytest.mark.asyncio
async def test_admin_attendance_update_is_audited(client, admin_token, db_session):
    # Create an attendance row for the admin user directly.
    admin = db_session.query(User).filter(User.email == "admin@test.com").first()
    assert admin is not None
    from app.core.time_utils import today_local

    record = Attendance(user_id=admin.id, date=today_local(), status="absent")
    db_session.add(record)
    db_session.commit()

    resp = await client.put(
        f"/admin/attendance/{record.id}",
        data={"status": "present", "time_in": "09:30"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "attendance.update")
        .first()
    )
    assert entry is not None, "admin attendance edit must produce an audit record"
    assert entry.entity_type == "attendance"
    assert entry.entity_id == str(record.id)
    assert entry.actor_email == "admin@test.com"
    assert entry.details["to_status"] == "present"


@pytest.mark.asyncio
async def test_admin_attendance_update_rejects_unknown_status(client, admin_token, db_session):
    admin = db_session.query(User).filter(User.email == "admin@test.com").first()
    from app.core.time_utils import today_local

    record = Attendance(user_id=admin.id, date=today_local(), status="absent")
    db_session.add(record)
    db_session.commit()

    resp = await client.put(
        f"/admin/attendance/{record.id}",
        data={"status": "on_vacation"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400, resp.text
    db_session.expire_all()
    refreshed = db_session.get(Attendance, record.id)
    assert refreshed.status == "absent", "invalid status must not be persisted"
