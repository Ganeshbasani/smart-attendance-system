"""Integration tests for session lifecycle + decision API (AttendX Phase 7)."""

import pytest

from tests.conftest import login_user, register_user


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def make_student(client, admin_token, email, roll):
    resp = await client.post("/api/v1/students", headers=auth(admin_token), json={
        "email": email, "password": "StudentPass1!", "full_name": "Session Student",
        "roll_number": roll,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


async def create_and_start(client, admin_token, name="Lab 1"):
    resp = await client.post("/api/v1/sessions", headers=auth(admin_token), json={"name": name})
    assert resp.status_code == 201, resp.text
    session = resp.json()
    started = await client.post(f"/api/v1/sessions/{session['id']}/start", headers=auth(admin_token))
    assert started.status_code == 200, started.text
    return session


@pytest.mark.asyncio
async def test_session_lifecycle_and_role_guards(client, admin_token):
    h = auth(admin_token)
    student_data = await register_user(client, "sess-student@test.com", "StudentPass1!")
    student_token = await login_user(client, "sess-student@test.com", "StudentPass1!")
    sh = auth(student_token)

    # Student cannot create/stop sessions.
    assert (await client.post("/api/v1/sessions", headers=sh, json={"name": "X"})).status_code == 403

    created = await client.post("/api/v1/sessions", headers=h, json={"name": "Lab A"})
    assert created.status_code == 201
    sid = created.json()["id"]
    assert created.json()["status"] == "draft"

    # Cannot submit a decision before start.
    bad = await client.post(f"/api/v1/sessions/{sid}/decisions", headers=h, json={
        "user_id": 1, "confidence": 90, "quality_score": 90, "liveness_ok": True,
    })
    assert bad.status_code == 200 and bad.json()["decision"] == "REJECTED"

    assert (await client.post(f"/api/v1/sessions/{sid}/start", headers=h)).json()["status"] == "active"
    assert (await client.post(f"/api/v1/sessions/{sid}/start", headers=h)).status_code == 409
    assert (await client.post(f"/api/v1/sessions/{sid}/stop", headers=h)).json()["status"] == "closed"
    assert (await client.post(f"/api/v1/sessions/{sid}/stop", headers=h)).status_code == 409


@pytest.mark.asyncio
async def test_decision_outcomes_and_duplicate(client, admin_token):
    h = auth(admin_token)
    student = await make_student(client, admin_token, "dec-student@test.com", "DEC001")
    session = await create_and_start(client, admin_token, "Decision Lab")
    sid = session["id"]

    good = {"user_id": student["user_id"], "confidence": 85, "quality_score": 80,
            "liveness_ok": True, "model_version": "buffalo_l"}
    verified = await client.post(f"/api/v1/sessions/{sid}/decisions", headers=h, json=good)
    assert verified.status_code == 200, verified.text
    assert verified.json()["decision"] == "VERIFIED"

    # Duplicate submission does not change the original decision.
    dup = await client.post(f"/api/v1/sessions/{sid}/decisions", headers=h, json=good)
    assert dup.json()["decision"] == "VERIFIED"

    records = await client.get(f"/api/v1/sessions/{sid}/records", headers=h)
    assert len(records.json()) == 1  # one row per student per session
    events = await client.get(f"/api/v1/sessions/{sid}/events", headers=h)
    assert len(events.json()) == 2  # both attempts logged


@pytest.mark.asyncio
async def test_review_queue_and_manual_override(client, admin_token):
    h = auth(admin_token)
    student = await make_student(client, admin_token, "rev-student@test.com", "REV001")
    session = await create_and_start(client, admin_token, "Review Lab")
    sid = session["id"]

    # Low confidence -> REVIEW_REQUIRED.
    low = await client.post(f"/api/v1/sessions/{sid}/decisions", headers=h, json={
        "user_id": student["user_id"], "confidence": 30, "quality_score": 80,
        "liveness_ok": True,
    })
    assert low.json()["decision"] == "REVIEW_REQUIRED"

    review = await client.post(f"/api/v1/sessions/{sid}/review/{student['user_id']}",
        headers=h, json={"decision": "VERIFIED", "reason": "Checked ID card manually"})
    assert review.status_code == 200, review.text
    assert review.json()["decision"] == "VERIFIED"

    # Manual override requires a reason.
    bad = await client.post(f"/api/v1/sessions/{sid}/manual", headers=h, json={
        "user_id": student["user_id"], "reason": "x",
    })
    assert bad.status_code == 422
    # Manual override replaces the reviewed decision (one row per student).
    override = await client.post(f"/api/v1/sessions/{sid}/manual", headers=h, json={
        "user_id": student["user_id"], "decision": "REJECTED",
        "reason": "Proxy detected by teacher observation",
    })
    assert override.json()["decision"] == "MANUAL_OVERRIDE"

    records = await client.get(f"/api/v1/sessions/{sid}/records", headers=h)
    assert len(records.json()) == 1  # still one row per student
    assert records.json()[0]["decision"] == "MANUAL_OVERRIDE"
    assert "Proxy detected" in records.json()[0]["reason"]


@pytest.mark.asyncio
async def test_spoof_is_never_accepted(client, admin_token):
    h = auth(admin_token)
    student = await make_student(client, admin_token, "spoof-student@test.com", "SPOOF1")
    session = await create_and_start(client, admin_token, "Spoof Lab")
    sid = session["id"]
    resp = await client.post(f"/api/v1/sessions/{sid}/decisions", headers=h, json={
        "user_id": student["user_id"], "confidence": 99, "quality_score": 99,
        "liveness_ok": True, "spoof_suspected": True,
    })
    assert resp.json()["decision"] == "REJECTED"


@pytest.mark.asyncio
async def test_student_cannot_submit_untrusted_session_decisions(client, admin_token):
    h = auth(admin_token)
    a = await make_student(client, admin_token, "self-a@test.com", "SELF-A")
    token = await login_user(client, "self-a@test.com", "StudentPass1!")
    sh = auth(token)
    session = await create_and_start(client, admin_token, "Scoped Lab")
    resp = await client.post(f"/api/v1/sessions/{session['id']}/decisions", headers=sh, json={
        "user_id": a["user_id"], "confidence": 90, "quality_score": 90, "liveness_ok": True,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_decision_submission_requires_authentication(client, admin_token):
    student = await make_student(client, admin_token, "anonymous-target@test.com", "ANON001")
    session = await create_and_start(client, admin_token, "Authenticated Lab")
    response = await client.post(f"/api/v1/sessions/{session['id']}/decisions", json={
        "user_id": student["user_id"], "confidence": 99, "quality_score": 99,
        "liveness_ok": True,
    })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_read_session_event_feed(client, admin_token):
    student = await make_student(client, admin_token, "private-events@test.com", "PRIV001")
    token = await login_user(client, "private-events@test.com", "StudentPass1!")
    session = await create_and_start(client, admin_token, "Private Feed Lab")
    response = await client.get(
        f"/api/v1/sessions/{session['id']}/events", headers=auth(token)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manual_roster_marks_present_absent_and_reports(client, admin_token):
    h = auth(admin_token)
    students = []
    for i in range(2):
        response = await client.post("/api/v1/students", headers=h, json={
            "email": f"manual-{i}@test.com", "password": "StudentPass1!",
            "full_name": f"Manual Student {i}", "roll_number": f"MAN-{i}",
        })
        assert response.status_code == 201, response.text
        students.append(response.json())

    klass = await client.post("/api/v1/classes", headers=h, json={
        "name": "Manual Roll Class", "code": "MAN-ROLL",
    })
    assert klass.status_code == 201, klass.text
    class_id = klass.json()["id"]
    for student in students:
        enrolled = await client.post(
            f"/api/v1/classes/{class_id}/enrollments", headers=h,
            json={"student_id": student["id"]},
        )
        assert enrolled.status_code == 201, enrolled.text

    created = await client.post("/api/v1/sessions", headers=h, json={
        "name": "Physical Roll Call", "class_section_id": class_id, "mode": "manual",
    })
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    assert created.json()["attendance_mode"] == "manual"
    assert (await client.post(f"/api/v1/sessions/{session_id}/start", headers=h)).status_code == 200

    roster = await client.get(f"/api/v1/sessions/{session_id}/roster", headers=h)
    assert roster.status_code == 200 and len(roster.json()) == 2
    incomplete = await client.put(f"/api/v1/sessions/{session_id}/manual-attendance", headers=h, json={
        "entries": [{"user_id": students[0]["user_id"], "status": "present"}],
    })
    assert incomplete.status_code == 422
    assert (await client.post(f"/api/v1/sessions/{session_id}/stop", headers=h)).status_code == 409

    marked = await client.put(f"/api/v1/sessions/{session_id}/manual-attendance", headers=h, json={
        "entries": [
            {"user_id": students[0]["user_id"], "status": "present"},
            {"user_id": students[1]["user_id"], "status": "absent"},
        ],
    })
    assert marked.status_code == 200, marked.text
    assert {row["attendance_status"] for row in marked.json()} == {"present", "absent"}
    assert (await client.post(f"/api/v1/sessions/{session_id}/stop", headers=h)).status_code == 200

    report = await client.get(
        f"/api/v1/sessions/reports/manual?class_section_id={class_id}&group_by=day", headers=h
    )
    assert report.status_code == 200, report.text
    group = report.json()["groups"][0]
    assert group["present"] == 1 and group["absent"] == 1
    assert group["attendance_percentage"] == 50.0
    assert all(student["attendance_percentage"] in (0.0, 100.0) for student in group["students"])
