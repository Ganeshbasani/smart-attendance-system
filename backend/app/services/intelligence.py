from math import ceil, floor
from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import AttendanceRecord, ClassSession, Enrollment, Subject, Student


def subject_stats(db: Session, student_id: str, subject_id: int):
    records = db.scalars(select(AttendanceRecord).join(ClassSession).where(AttendanceRecord.student_id == student_id, ClassSession.subject_id == subject_id)).all()
    attended = sum(r.status == "Present" for r in records)
    conducted = sum(r.status in {"Present", "Absent", "Excused"} for r in records)
    excused = sum(r.status == "Excused" for r in records)
    subject = db.get(Subject, subject_id)
    return {"attended": attended, "conducted": conducted, "excused": excused, "threshold": subject.threshold if subject else 75.0, "planned_sessions": subject.planned_sessions if subject else conducted + 10, "subject": subject}


def runway(stats: dict):
    attended, conducted, threshold = stats["attended"], stats["conducted"], stats["threshold"] / 100.0
    remaining = max(0, stats["planned_sessions"] - conducted)
    current = (attended / conducted * 100) if conducted else 100.0
    safe_miss = max(0, min(remaining, floor(attended / threshold - conducted))) if threshold else remaining
    projected = ((attended + remaining) / (conducted + remaining) * 100) if (conducted + remaining) else current
    recoverable = ((attended + remaining) / (conducted + remaining) * 100) >= threshold * 100 if (conducted + remaining) else current >= threshold * 100
    needed_all_remaining = max(0, min(remaining, ceil(threshold * (conducted + remaining) - attended)))
    next_window = min(7, remaining)
    needed_next_window = max(0, min(next_window, ceil(threshold * (conducted + next_window) - attended)))
    if remaining == 0:
        needed_all_remaining = 0
        needed_next_window = 0
    return {
        "current_percent": round(current, 1),
        "threshold": round(threshold * 100, 1),
        "remaining": remaining,
        "safe_miss": safe_miss,
        "required_to_recover": needed_all_remaining,
        "next_window": next_window,
        "required_in_next_window": needed_next_window,
        "recoverable": bool(recoverable),
        "projected_end_percent": round(projected, 1),
    }


def risk(stats: dict):
    r = runway(stats)
    recent = stats.get("recent_percent", r["current_percent"])
    consecutive_absences = stats.get("consecutive_absences", 0)
    gap = r["current_percent"] - r["threshold"]
    if r["current_percent"] < r["threshold"] - 10 and not r["recoverable"]:
        state = "Critical"
    elif gap < 0 or r["projected_end_percent"] < r["threshold"]:
        state = "At Risk"
    elif recent < r["threshold"] or consecutive_absences >= 2:
        state = "Watch"
    else:
        state = "Safe"
    reasons = []
    if gap < 0: reasons.append(f"attendance is {abs(round(gap,1))} percentage points below the {r['threshold']:g}% threshold")
    if recent < r["threshold"]: reasons.append("the recent attendance trend is below the threshold")
    if consecutive_absences >= 2: reasons.append(f"there are {consecutive_absences} consecutive absences")
    if r["remaining"] <= 7 and r["projected_end_percent"] < r["threshold"]: reasons.append("few sessions remain to recover")
    if not reasons: reasons.append("recent attendance remains within the expected safe range")
    return {"state": state, "reason": "; ".join(reasons), **r}


def student_subject_intelligence(db: Session, student_id: str):
    rows = db.execute(select(Subject).join(Enrollment, Enrollment.subject_id == Subject.id).join(Student, Student.id == Enrollment.student_id).where(Student.student_id == student_id)).scalars().all()
    out = []
    for subj in rows:
        stats = subject_stats(db, student_id, subj.id)
        records = db.scalars(select(AttendanceRecord).join(ClassSession).where(AttendanceRecord.student_id == student_id, ClassSession.subject_id == subj.id).order_by(AttendanceRecord.marked_at.desc())).all()
        recent_window = records[:10]
        recent_percent = sum(r.status == "Present" for r in recent_window) / len(recent_window) * 100 if recent_window else stats["threshold"]
        consecutive = 0
        for rec in records:
            if rec.status == "Absent": consecutive += 1
            elif rec.status == "Present": break
        stats["recent_percent"] = recent_percent
        stats["consecutive_absences"] = consecutive
        intel = risk(stats)
        intel.update({"subject_id": subj.id, "code": subj.code, "name": subj.name})
        out.append(intel)
    return out
