from datetime import date, timedelta, datetime, timezone
import csv
import hashlib
import random
from pathlib import Path

from auth import hash_password
from config import BASE_DIR
from db import get_conn, init_db, utc_now_iso


def seed():
    init_db()
    student_csv = BASE_DIR / "data" / "students.csv"
    if not student_csv.exists():
        legacy = BASE_DIR / "students.csv"
        if legacy.exists():
            student_csv = legacy

    with get_conn() as conn:
        students = []
        with open(student_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                students.append({
                    "student_id": str(row["student_id"]),
                    "name": row["name"],
                    "department": row["department"],
                    "year": int(row["year"]),
                })

        for st in students:
            conn.execute(
                """INSERT OR IGNORE INTO students(student_id,name,department,year,created_at)
                   VALUES (?,?,?,?,?)""",
                (st["student_id"], st["name"], st["department"], st["year"], utc_now_iso()),
            )

        users = [
            ("admin", "AttendX Admin", "admin", "admin123", None, None),
            ("hod", "Department HOD", "hod", "hod123", None, "CSE"),
            ("faculty", "Demo Faculty", "faculty", "faculty123", None, "CSE"),
            ("student1", students[0]["name"], "student", "student123", students[0]["student_id"], students[0]["department"]),
            ("student2", students[1]["name"], "student", "student123", students[1]["student_id"], students[1]["department"]),
        ]
        for username, full_name, role, password, student_id, department in users:
            conn.execute(
                """INSERT OR IGNORE INTO users(username,full_name,role,password_hash,student_id,department,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (username, full_name, role, hash_password(password), student_id, department, utc_now_iso()),
            )

        subjects = [
            ("CS301", "Database Management Systems", "CSE", "VI", 75, 32, 1.2),
            ("CS302", "Operating Systems", "CSE", "VI", 75, 32, 1.2),
            ("CS303", "Computer Networks", "CSE", "VI", 75, 32, 1.1),
            ("CS304", "Software Engineering", "CSE", "VI", 75, 30, 1.0),
            ("CS305", "Artificial Intelligence", "CSE", "VI", 75, 28, 1.2),
            ("IT301", "Data Communication", "IT", "VI", 75, 30, 1.0),
            ("EE301", "Control Systems", "EEE", "VI", 75, 30, 1.0),
        ]
        for row in subjects:
            conn.execute(
                """INSERT OR IGNORE INTO subjects(code,name,department,semester,threshold,planned_sessions,weight)
                   VALUES (?,?,?,?,?,?,?)""",
                row,
            )

        all_subjects = conn.execute("SELECT id,code,department FROM subjects").fetchall()
        for subject in all_subjects:
            for st in students:
                if st["department"] == subject["department"] or subject["department"] == "CSE":
                    conn.execute(
                        "INSERT OR IGNORE INTO enrollments(student_id,subject_id) VALUES (?,?)",
                        (st["student_id"], subject["id"]),
                    )

        faculty_id = conn.execute("SELECT id FROM users WHERE username='faculty'").fetchone()[0]
        dates = [date.today() - timedelta(days=i) for i in range(1, 56) if (date.today() - timedelta(days=i)).weekday() < 6]
        dates = list(reversed(dates))
        for subject in all_subjects:
            existing = conn.execute("SELECT COUNT(*) FROM class_sessions WHERE subject_id=?", (subject["id"],)).fetchone()[0]
            if existing:
                continue
            for d in dates[:22]:
                sid = conn.execute(
                    """INSERT INTO class_sessions(subject_id,session_date,start_time,end_time,status,qr_secret,created_by,created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (subject["id"], d.isoformat(), "10:00", "11:00", "closed", hashlib.sha256(f"{subject['id']}:{d}".encode()).hexdigest()[:32], faculty_id, datetime(d.year, d.month, d.day, 10, 0, tzinfo=timezone.utc).isoformat()),
                ).lastrowid
                for st in students:
                    enrolled = conn.execute(
                        "SELECT 1 FROM enrollments WHERE student_id=? AND subject_id=?",
                        (st["student_id"], subject["id"]),
                    ).fetchone()
                    if not enrolled:
                        continue
                    # Stable demo behaviour with recent dip for selected students.
                    n = int(st["student_id"])
                    base = 0.91 - (n % 7) * 0.035
                    recency_dip = 0.12 if n % 13 in (0, 1) and d >= dates[15] else 0
                    seed_val = f"{subject['code']}:{st['student_id']}:{d.isoformat()}"
                    rnd = random.Random(seed_val)
                    present = rnd.random() < max(0.45, base - recency_dip)
                    if present:
                        conn.execute(
                            """INSERT INTO attendance_records(session_id,student_id,status,marked_at,source)
                               VALUES (?,?,?,?,?)""",
                            (sid, st["student_id"], "Present", datetime(d.year, d.month, d.day, 11, 0, tzinfo=timezone.utc).isoformat(), "Seeded history"),
                        )
        conn.commit()

    print("AttendX seed complete.")


if __name__ == "__main__":
    seed()
