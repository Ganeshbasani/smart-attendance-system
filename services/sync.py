from db import audit, execute, query_one, utc_now_iso


def apply_queue(queue_payload, actor_user_id):
    if not isinstance(queue_payload, list):
        raise ValueError("Sync payload must be a JSON list.")

    applied = 0
    rejected = 0
    results = []
    for event in queue_payload:
        client_id = str(event.get("client_event_id", "")).strip()
        session_id = event.get("session_id")
        student_id = str(event.get("student_id", "")).strip()
        status = event.get("status", "Absent")
        if not client_id or not session_id or not student_id or status not in {"Present", "Absent", "Excused"}:
            rejected += 1
            results.append({"client_event_id": client_id, "status": "Rejected", "reason": "Invalid event"})
            continue

        prior = query_one("SELECT status FROM sync_events WHERE client_event_id=?", (client_id,))
        if prior:
            results.append({"client_event_id": client_id, "status": "Already applied"})
            continue

        try:
            session = query_one("SELECT id FROM class_sessions WHERE id=? AND status<>'cancelled'", (int(session_id),))
            enrolled = query_one(
                """SELECT 1 FROM enrollments e
                   JOIN class_sessions cs ON cs.subject_id=e.subject_id
                   WHERE cs.id=? AND e.student_id=?""",
                (int(session_id), student_id),
            )
            if not session or not enrolled:
                raise ValueError("Session or enrollment not valid.")

            execute(
                "INSERT INTO sync_events(client_event_id,payload_json,status,created_at,applied_at) VALUES (?,?, 'Applied',?,?)",
                (client_id, __import__("json").dumps(event), utc_now_iso(), utc_now_iso()),
            )
            execute(
                """INSERT INTO attendance_records(session_id,student_id,status,marked_at,source)
                   VALUES (?,?,?,?, 'Offline sync')
                   ON CONFLICT(session_id,student_id)
                   DO UPDATE SET status=excluded.status, marked_at=excluded.marked_at, source='Offline sync'""",
                (int(session_id), student_id, status, utc_now_iso()),
            )
            applied += 1
            results.append({"client_event_id": client_id, "status": "Applied"})
        except Exception as exc:
            execute(
                "INSERT INTO sync_events(client_event_id,payload_json,status,created_at,reason) VALUES (?,?, 'Rejected',?,?)",
                (client_id, __import__("json").dumps(event), utc_now_iso(), str(exc)),
            )
            rejected += 1
            results.append({"client_event_id": client_id, "status": "Rejected", "reason": str(exc)})
    audit(actor_user_id, "sync_offline_queue", "sync_batch", None, {"applied": applied, "rejected": rejected})
    return {"applied": applied, "rejected": rejected, "results": results}
