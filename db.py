import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student','faculty','hod','admin')),
    password_hash TEXT NOT NULL,
    student_id TEXT,
    department TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    year INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    semester TEXT NOT NULL,
    threshold REAL NOT NULL DEFAULT 75.0,
    planned_sessions INTEGER NOT NULL DEFAULT 32,
    weight REAL NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_id TEXT NOT NULL,
    subject_id INTEGER NOT NULL,
    PRIMARY KEY(student_id, subject_id),
    FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS class_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    session_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed','cancelled')),
    qr_secret TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(subject_id) REFERENCES subjects(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('Present','Absent','Excused')),
    marked_at TEXT NOT NULL,
    source TEXT NOT NULL,
    device_id TEXT,
    token_id TEXT,
    UNIQUE(session_id, student_id),
    FOREIGN KEY(session_id) REFERENCES class_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attendance_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    student_id TEXT,
    attempted_at TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT,
    device_id TEXT,
    token_id TEXT,
    FOREIGN KEY(session_id) REFERENCES class_sessions(id),
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS device_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    device_hash TEXT NOT NULL,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_seen TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(student_id, device_hash),
    FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    student_id TEXT,
    priority TEXT NOT NULL CHECK(priority IN ('Critical','High','Medium','Informational')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    dedupe_key TEXT,
    read_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject_id INTEGER,
    trigger_type TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    owner_role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','In Progress','Resolved')),
    due_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY(subject_id) REFERENCES subjects(id)
);

CREATE TABLE IF NOT EXISTS correction_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    requested_status TEXT NOT NULL CHECK(requested_status IN ('Present','Absent','Excused')),
    reason TEXT NOT NULL,
    document_name TEXT,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
    requested_by INTEGER NOT NULL,
    reviewed_by INTEGER,
    review_note TEXT,
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    FOREIGN KEY(session_id) REFERENCES class_sessions(id),
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    FOREIGN KEY(requested_by) REFERENCES users(id),
    FOREIGN KEY(reviewed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS condonation_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    document_name TEXT,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
    requested_by INTEGER NOT NULL,
    reviewed_by INTEGER,
    review_note TEXT,
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    FOREIGN KEY(subject_id) REFERENCES subjects(id),
    FOREIGN KEY(requested_by) REFERENCES users(id),
    FOREIGN KEY(reviewed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sync_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_event_id TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Applied','Rejected')),
    created_at TEXT NOT NULL,
    applied_at TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(actor_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance_records(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance_records(session_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, read_at);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_attempts_session ON attendance_attempts(session_id);
"""


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 20000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        defaults = {
            "attendance_threshold": "75",
            "semester_label": "2026–27 Semester",
            "semester_end": "2027-04-30",
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)",
                (key, value),
            )


def execute(sql, params=()):
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def query_one(sql, params=()):
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def query_all(sql, params=()):
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def audit(actor_user_id, action, entity_type, entity_id=None, details=None):
    execute(
        """INSERT INTO audit_logs(actor_user_id,action,entity_type,entity_id,details_json,created_at)
           VALUES (?,?,?,?,?,?)""",
        (
            actor_user_id,
            action,
            entity_type,
            str(entity_id) if entity_id is not None else None,
            json.dumps(details or {}, default=str),
            utc_now_iso(),
        ),
    )


def get_setting(key, default=None):
    row = query_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key, value, actor_user_id=None):
    execute(
        """INSERT INTO settings(key,value) VALUES (?,?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
        (key, str(value)),
    )
    audit(actor_user_id, "update_setting", "setting", key, {"value": str(value)})
