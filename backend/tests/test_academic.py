"""Tests for AttendX Phase 2: academic domain, 3 roles, and /api/v1 aliases."""

import pytest

from tests.conftest import login_user, register_user


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── v1 aliases + role defaults ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_registration_is_student_and_v1_alias_works(client):
    data = await register_user(client, "newbie@test.com", "StudentPass1!", "New Student")
    assert data["user"]["role"] == "student"

    # Legacy login path still works.
    token = await login_user(client, "newbie@test.com", "StudentPass1!")
    # Additive v1 alias serves the same endpoint.
    resp = await client.post("/api/v1/auth/login", json={
        "email": "newbie@test.com", "password": "StudentPass1!"
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]

    profile = await client.get("/api/v1/user/profile", headers=auth(token))
    assert profile.status_code == 200, profile.text

    me = await client.get("/api/v1/auth/me", headers=auth(token))
    assert me.status_code == 200, me.text
    assert me.json()["user"]["email"] == "newbie@test.com"
    legacy_me = await client.get("/auth/me", headers=auth(token))
    assert legacy_me.status_code == 200


# ── full academic CRUD by admin ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_manages_full_academic_domain(client, admin_token):
    h = auth(admin_token)

    dept = await client.post("/api/v1/departments", headers=h, json={"name": "Computer Science", "code": "CSE"})
    assert dept.status_code == 201, dept.text
    dept_id = dept.json()["id"]

    session = await client.post("/api/v1/academic-sessions", headers=h, json={
        "name": "2026-27 Odd", "start_date": "2026-07-01", "end_date": "2026-12-31", "is_active": True,
    })
    assert session.status_code == 201, session.text
    session_id = session.json()["id"]

    course = await client.post("/api/v1/courses", headers=h, json={
        "name": "Data Structures", "code": "CS201", "department_id": dept_id, "credits": 4,
    })
    assert course.status_code == 201, course.text
    course_id = course.json()["id"]

    teacher = await client.post("/api/v1/teachers", headers=h, json={
        "email": "teacher@test.com", "password": "TeacherPass1!", "full_name": "Dr. Rao",
        "employee_id": "EMP-001", "department_id": dept_id,
    })
    assert teacher.status_code == 201, teacher.text
    teacher_id = teacher.json()["id"]
    assert teacher.json()["email"] == "teacher@test.com"

    student = await client.post("/api/v1/students", headers=h, json={
        "email": "student@test.com", "password": "StudentPass1!", "full_name": "A Student",
        "roll_number": "21CS001", "department_id": dept_id, "academic_session_id": session_id,
    })
    assert student.status_code == 201, student.text
    student_id = student.json()["id"]
    assert student.json()["role"] == "student"

    klass = await client.post("/api/v1/classes", headers=h, json={
        "name": "CS201 Section A", "code": "CS201-A", "course_id": course_id,
        "teacher_id": teacher_id, "academic_session_id": session_id,
    })
    assert klass.status_code == 201, klass.text
    class_id = klass.json()["id"]

    enroll = await client.post(f"/api/v1/classes/{class_id}/enrollments", headers=h, json={"student_id": student_id})
    assert enroll.status_code == 201, enroll.text
    assert enroll.json()["roll_number"] == "21CS001"

    listing = await client.get("/api/v1/classes", headers=h)
    assert listing.status_code == 200
    assert listing.json()[0]["student_count"] == 1

    students = await client.get(f"/api/v1/classes/{class_id}/students", headers=h)
    assert len(students.json()) == 1
    assert students.json()[0]["full_name"] == "A Student"

    # Reads on all list endpoints work for admin.
    for path in ("/api/v1/departments", "/api/v1/courses", "/api/v1/academic-sessions",
                 "/api/v1/teachers", "/api/v1/students"):
        r = await client.get(path, headers=h)
        assert r.status_code == 200, (path, r.text)


# ── role-based authorization ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_role_permissions(client, admin_token):
    h = auth(admin_token)

    st = await client.post("/api/v1/students", headers=h, json={
        "email": "perm-student@test.com", "password": "StudentPass1!",
        "full_name": "Perm Student", "roll_number": "PERM001",
    })
    student_id = st.json()["id"]
    student_token = await login_user(client, "perm-student@test.com", "StudentPass1!")
    sh = auth(student_token)

    teacher = await client.post("/api/v1/teachers", headers=h, json={
        "email": "perm-teacher@test.com", "password": "TeacherPass1!",
        "full_name": "Perm Teacher", "employee_id": "EMP-PERM",
    })
    assert teacher.status_code == 201
    teacher_token = await login_user(client, "perm-teacher@test.com", "TeacherPass1!")
    th = auth(teacher_token)

    # Students and teachers cannot create departments; staff guard works.
    for token_header in (sh, th):
        r = await client.post("/api/v1/departments", headers=token_header, json={"name": "Nope"})
        assert r.status_code == 403, r.text

    # Student can read only their own profile/list.
    me = await client.get("/api/v1/students/me", headers=sh)
    assert me.status_code == 200 and me.json()["id"] == student_id
    own_list = await client.get("/api/v1/students", headers=sh)
    assert [s["id"] for s in own_list.json()] == [student_id]

    # Teacher can read academic data.
    assert (await client.get("/api/v1/students", headers=th)).status_code == 200
    assert (await client.get("/api/v1/classes", headers=th)).status_code == 200
    # But teacher cannot create a class (admin-only mutation).
    assert (await client.post("/api/v1/classes", headers=th, json={
        "name": "X", "code": "X1"
    })).status_code == 403


# ── validation & uniqueness ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_uniqueness_and_fk_validation(client, admin_token):
    h = auth(admin_token)

    dep = await client.post("/api/v1/departments", headers=h, json={"name": "Physics", "code": "PHY"})
    dep_id = dep.json()["id"]

    assert (await client.post("/api/v1/departments", headers=h, json={"name": "Physics"})).status_code == 409

    student_payload = {
        "email": "unique@test.com", "password": "StudentPass1!",
        "full_name": "Unique", "roll_number": "U001",
    }
    first = await client.post("/api/v1/students", headers=h, json=student_payload)
    assert first.status_code == 201
    duplicate = await client.post("/api/v1/students", headers=h, json={
        **student_payload, "email": "other@test.com"
    })
    assert duplicate.status_code == 409, duplicate.text

    bad_fk = await client.post("/api/v1/courses", headers=h, json={
        "name": "Bad", "code": "BAD1", "department_id": 99999,
    })
    assert bad_fk.status_code == 404, bad_fk.text

    klass = await client.post("/api/v1/classes", headers=h, json={"name": "C", "code": "C-1"})
    class_id = klass.json()["id"]
    enroll_payload = {"student_id": first.json()["id"]}
    assert (await client.post(f"/api/v1/classes/{class_id}/enrollments", headers=h, json=enroll_payload)).status_code == 201
    assert (await client.post(f"/api/v1/classes/{class_id}/enrollments", headers=h, json=enroll_payload)).status_code == 409

    missing = await client.get("/api/v1/students/99999", headers=h)
    assert missing.status_code == 404

    # Partial updates must not require a password (management UI enabler).
    partial = await client.put(f"/api/v1/students/{first.json()['id']}", headers=h,
                               json={"full_name": "Renamed Student"})
    assert partial.status_code == 200, partial.text
    assert partial.json()["full_name"] == "Renamed Student"
    assert partial.json()["roll_number"] == "U001"


# ── pagination & audit ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pagination_and_audit_log(client, admin_token):
    h = auth(admin_token)
    for i in range(3):
        r = await client.post("/api/v1/departments", headers=h, json={"name": f"Dept {i}", "code": f"D{i}"})
        assert r.status_code == 201

    first_page = await client.get("/api/v1/departments?skip=0&limit=2", headers=h)
    second_page = await client.get("/api/v1/departments?skip=2&limit=2", headers=h)
    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1

    # Validation on query params.
    assert (await client.get("/api/v1/departments?limit=0", headers=h)).status_code == 422

    logs = await client.get("/admin/audit-logs", headers=h)
    assert logs.status_code == 200
    body = logs.json()
    rows = body if isinstance(body, list) else body.get("logs", [])
    actions = [row["action"] for row in rows]
    assert "academic.department.create" in actions
