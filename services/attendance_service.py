import base64
import hashlib
import hmac
import json
import math
import secrets
from datetime import datetime, timezone, timedelta

from config import SECRET_KEY, TIMEZONE_NAME
from zoneinfo import ZoneInfo
from db import audit, execute, query_all, query_one, utc_now_iso
from services.risk_engine import runway, risk_state


def device_hash(raw_device_id: str) -> str:
    return hashlib.sha256(f"{SECRET_KEY}:{raw_device_id}".encode()).hexdigest()


def build_token(session_id: int, expires_at: datetime) -> str:
    payload = {"sid": int(session_id), "exp": int(expires_at.timestamp()), "nonce": secrets.token_hex(6)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), raw, hashlib.sha256).hexdigest()[:24]
    return f"AX1.{encoded}.{sig}"


def decode_token(token: str):
    try:
        prefix, encoded, sig = token.split(".")
        if prefix != "AX1":
            raise ValueError("Unsupported token")
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        expected = hmac.new(SECRET_KEY.encode(), raw, hashlib.sha256).hexdigest()[:24]
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Invalid token signature")
        payload = json.loads(raw.decode())
        return payload
    except Exception as exc:
        raise ValueError("Invalid attendance token") from exc


def create_session(subject_id, faculty_user_id, start_time, end_time, ttl_seconds=45):
    now = datetime.now(ZoneInfo(TIMEZONE_NAME))
    secret = secrets.token_hex(16)
    session_id = execute(
        """INSERT INTO class_sessions(subject_id,session_date,start_time,end_time,status,qr_secret,created_by,created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            subject_id,
            now.date().isoformat(),
            start_time,
            end_time,
            "open",
            secret,
            faculty_user_id,
            utc_now_iso(),
        ),
    )
    audit(faculty_user_id, "create_attendance_session", "class_session", session_id, {"subject_id": subject_id})
    return session_id


def session_token(session_id, ttl_seconds=45):
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return build_token(session_id, expires), expires


def record_attempt(session_id, student_id, status, reason, raw_device_id, token_id):
    execute(
        """INSERT INTO attendance_attempts(session_id,student_id,attempted_at,status,reason,device_id,token_id)
           VALUES (?,?,?,?,?,?,?)""",
        (
            session_id,
            student_id,
            utc_now_iso(),
            status,
            reason,
            device_hash(raw_device_id) if raw_device_id else None,
            token_id,
        ),
    )


def submit_qr_attendance(token, student_id, raw_device_id):
    payload = decode_token(token)
    session_id = int(payload["sid"])
    token_id = hashlib.sha256(token.encode()).hexdigest()[:12]
    student = query_one("SELECT * FROM students WHERE student_id=?", (student_id,))
    session = query_one(
        """SELECT cs.*, s.name as subject_name, s.code as subject_code
           FROM class_sessions cs JOIN subjects s ON s.id=cs.subject_id
           WHERE cs.id=?""",
        (session_id,),
    )
    if not student or not session:
        record_attempt(session_id, student_id, "Rejected", "Unknown student or session", raw_device_id, token_id)
        raise ValueError("Student or attendance session could not be verified.")

    now = datetime.now(timezone.utc)
    if int(payload.get("exp", 0)) < int(now.timestamp()):
        record_attempt(session_id, student_id, "Rejected", "Expired QR token", raw_device_id, token_id)
        raise ValueError("This QR has expired. Ask faculty to display the current code.")

    if session["status"] != "open":
        record_attempt(session_id, student_id, "Rejected", "Session closed", raw_device_id, token_id)
        raise ValueError("This attendance session is closed.")

    enrolled = query_one(
        "SELECT 1 FROM enrollments WHERE student_id=? AND subject_id=?",
        (student_id, session["subject_id"]),
    )
    if not enrolled:
        record_attempt(session_id, student_id, "Rejected", "Student not enrolled", raw_device_id, token_id)
        raise ValueError("You are not enrolled in this subject.")

    dup = query_one(
        "SELECT 1 FROM attendance_records WHERE session_id=? AND student_id=?",
        (session_id, student_id),
    )
    if dup:
        record_attempt(session_id, student_id, "Rejected", "Duplicate attendance", raw_device_id, token_id)
        raise ValueError("Attendance is already recorded for this session.")

    dhash = device_hash(raw_device_id)
    execute(
        """INSERT INTO device_registrations(student_id,device_hash,label,created_at,last_seen)
           VALUES (?,?,?,?,?)
           ON CONFLICT(student_id,device_hash)
           DO UPDATE SET last_seen=excluded.last_seen""",
        (student_id, dhash, "Registered browser device", utc_now_iso(), utc_now_iso()),
    )
    record_id = execute(
        """INSERT INTO attendance_records(session_id,student_id,status,marked_at,source,device_id,token_id)
           VALUES (?,?,?,?,?,?,?)""",
        (session_id, student_id, "Present", utc_now_iso(), "Dynamic QR", dhash, token_id),
    )
    audit(None, "record_attendance", "attendance_record", record_id, {"session_id": session_id, "student_id": student_id})
    record_attempt(session_id, student_id, "Accepted", "Verified", raw_device_id, token_id)
    return record_id


def mark_faculty_attendance(session_id, student_id, status, faculty_user_id):
    existing = query_one(
        "SELECT id FROM attendance_records WHERE session_id=? AND student_id=?",
        (session_id, student_id),
    )
    if existing:
        return existing["id"]
    record_id = execute(
        """INSERT INTO attendance_records(session_id,student_id,status,marked_at,source)
           VALUES (?,?,?,?,?)""",
        (session_id, student_id, status, utc_now_iso(), "Faculty"),
    )
    audit(faculty_user_id, "mark_attendance", "attendance_record", record_id, {"session_id": session_id, "student_id": student_id, "status": status})
    return record_id


def get_subject_stats(student_id, subject_id):
    subject = query_one("SELECT * FROM subjects WHERE id=?", (subject_id,))
    if not subject:
        return None
    row = query_one(
        """SELECT COUNT(*) as conducted,
                  SUM(CASE WHEN ar.status='Present' THEN 1 ELSE 0 END) as attended
           FROM class_sessions cs
           LEFT JOIN attendance_records ar
             ON ar.session_id=cs.id AND ar.student_id=?
           WHERE cs.subject_id=? AND cs.status <> 'cancelled'""",
        (student_id, subject_id),
    ) or {"conducted": 0, "attended": 0}
    conducted = int(row["conducted"] or 0)
    attended = int(row["attended"] or 0)
    remaining = max(0, int(subject["planned_sessions"]) - conducted)

    recent = query_all(
        """SELECT cs.session_date,
                  CASE WHEN ar.status='Present' THEN 1 ELSE 0 END as attended
           FROM class_sessions cs
           LEFT JOIN attendance_records ar
             ON ar.session_id=cs.id AND ar.student_id=?
           WHERE cs.subject_id=? AND cs.status <> 'cancelled'
           ORDER BY cs.session_date DESC LIMIT 8""",
        (student_id, subject_id),
    )
    recent_rate = (
        sum(r["attended"] for r in recent) / len(recent) * 100
        if recent else (attended / conducted * 100 if conducted else 0.0)
    )
    prior = query_all(
        """SELECT cs.session_date,
                  CASE WHEN ar.status='Present' THEN 1 ELSE 0 END as attended
           FROM class_sessions cs
           LEFT JOIN attendance_records ar ON ar.session_id=cs.id AND ar.student_id=?
           WHERE cs.subject_id=? AND cs.status <> 'cancelled'
           ORDER BY cs.session_date ASC LIMIT 8""",
        (student_id, subject_id),
    )
    prior_rate = (
        sum(r["attended"] for r in prior) / len(prior) * 100
        if prior else recent_rate
    )
    trend_pp = recent_rate - prior_rate

    ordered = list(reversed(recent))
    consecutive = 0
    for r in ordered:
        if r["attended"] == 0:
            consecutive += 1
        else:
            break

    projected_pct = (
        (attended + round(remaining * recent_rate / 100)) / (conducted + remaining) * 100
        if (conducted + remaining) else 0.0
    )
    r = runway(attended, conducted, remaining, float(subject["threshold"]))
    risk = risk_state(
        r["current_pct"], trend_pp, consecutive, remaining,
        r["recoverable"], projected_pct, float(subject["threshold"]), float(subject["weight"])
    )
    return {
        **r,
        "subject_id": subject_id,
        "subject_code": subject["code"],
        "subject_name": subject["name"],
        "department": subject["department"],
        "weight": subject["weight"],
        "recent_rate": round(recent_rate, 1),
        "trend_pp": round(trend_pp, 1),
        "consecutive_absences": consecutive,
        "projected_pct": round(projected_pct, 1),
        "risk_state": risk["state"],
        "risk_signals": risk["signals"],
    }


def get_student_dashboard(student_id):
    subjects = query_all(
        """SELECT s.* FROM subjects s
           JOIN enrollments e ON e.subject_id=s.id
           WHERE e.student_id=? ORDER BY s.code""",
        (student_id,),
    )
    return [get_subject_stats(student_id, s["id"]) for s in subjects]


def session_summary(session_id):
    session = query_one(
        """SELECT cs.*, s.code, s.name
           FROM class_sessions cs JOIN subjects s ON s.id=cs.subject_id
           WHERE cs.id=?""",
        (session_id,),
    )
    if not session:
        return None
    roster = query_all(
        """SELECT st.student_id, st.name,
                  COALESCE(ar.status,'Absent') as status,
                  ar.marked_at, ar.device_id, ar.source
           FROM students st
           JOIN enrollments e ON e.student_id=st.student_id
           LEFT JOIN attendance_records ar
             ON ar.student_id=st.student_id AND ar.session_id=?
           WHERE e.subject_id=?
           ORDER BY st.student_id""",
        (session_id, session["subject_id"]),
    )
    return {"session": session, "roster": roster}
