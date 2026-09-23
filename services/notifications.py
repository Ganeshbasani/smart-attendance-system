from db import execute, query_all, query_one, utc_now_iso


def _notify(user_id, student_id, priority, title, message, dedupe_key):
    existing = query_one(
        "SELECT id FROM notifications WHERE user_id=? AND dedupe_key=?",
        (user_id, dedupe_key),
    )
    if existing:
        return existing["id"]
    return execute(
        """INSERT INTO notifications(user_id,student_id,priority,title,message,dedupe_key,created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (user_id, student_id, priority, title, message, dedupe_key, utc_now_iso()),
    )


def refresh_student_notifications(student_id, subject_stats):
    user = query_one(
        "SELECT id FROM users WHERE student_id=? AND role='student'",
        (student_id,),
    )
    if not user:
        return 0

    created = 0
    for s in subject_stats:
        state = s["risk_state"]
        if state in ("Critical", "At Risk"):
            priority = "Critical" if state == "Critical" else "High"
            if s["recoverable"]:
                action = (
                    f"Attend the next {s['needed_next_window']} of the next "
                    f"{s['next_window']} planned sessions."
                )
            else:
                action = "Recovery is no longer mathematically possible."
            message = (
                f"{s['subject_code']} is {state.lower()}: current attendance "
                f"{s['current_pct']:.1f}%, projected {s['projected_pct']:.1f}%. {action}"
            )
            created += bool(
                _notify(
                    user["id"],
                    student_id,
                    priority,
                    f"{s['subject_code']} needs attention",
                    message,
                    f"risk:{student_id}:{s['subject_id']}:{s['risk_state']}",
                )
            )
        elif state == "Watch":
            created += bool(
                _notify(
                    user["id"],
                    student_id,
                    "Medium",
                    f"{s['subject_code']} moved to Watch",
                    f"Attendance is {s['current_pct']:.1f}% with a {s['trend_pp']:+.1f} pp recent trend.",
                    f"watch:{student_id}:{s['subject_id']}",
                )
            )
    return created


def list_notifications(user_id, unread_only=False):
    sql = "SELECT * FROM notifications WHERE user_id=?"
    params = [user_id]
    if unread_only:
        sql += " AND read_at IS NULL"
    sql += (
        " ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 "
        "WHEN 'Medium' THEN 3 ELSE 4 END, created_at DESC"
    )
    return query_all(sql, params)


def mark_read(notification_id, user_id):
    execute(
        "UPDATE notifications SET read_at=? WHERE id=? AND user_id=?",
        (utc_now_iso(), notification_id, user_id),
    )
