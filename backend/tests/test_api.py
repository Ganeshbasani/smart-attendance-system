from fastapi.testclient import TestClient
from app.main import app

def test_login_and_role_boundary():
    with TestClient(app) as c:
        r=c.post("/api/auth/login",json={"username":"student","password":"AttendX@2026"})
        assert r.status_code==200
        token=r.json()["access_token"]
        me=c.get("/api/me",headers={"Authorization":f"Bearer {token}"})
        assert me.status_code==200 and me.json()["role"]=="student"
        admin=c.get("/api/admin/system-health",headers={"Authorization":f"Bearer {token}"})
        assert admin.status_code==403

def test_live_qr_attendance_and_duplicate_protection():
    with TestClient(app) as c:
        st=c.post("/api/auth/login",json={"username":"student","password":"AttendX@2026"}).json()["access_token"]
        ft=c.post("/api/auth/login",json={"username":"faculty","password":"AttendX@2026"}).json()["access_token"]
        fh={"Authorization":f"Bearer {ft}"}; sh={"Authorization":f"Bearer {st}"}
        a=c.get("/api/faculty/assignments",headers=fh).json()[0]
        s=c.post("/api/faculty/sessions",headers=fh,json={"subject_id":a["subject_id"],"section_id":a["section_id"],"session_date":"2026-09-23","start_time":"10:00","end_time":"11:00"})
        assert s.status_code==200
        qr=c.get(f"/api/faculty/sessions/{s.json()['id']}/qr",headers=fh).json()["payload"]
        first=c.post("/api/student/attendance/scan",headers=sh,json={"qr_payload":qr,"device_id":"test-device-0001"})
        assert first.status_code==200
        dup=c.post("/api/student/attendance/scan",headers=sh,json={"qr_payload":qr,"device_id":"test-device-0001"})
        assert dup.status_code==400
