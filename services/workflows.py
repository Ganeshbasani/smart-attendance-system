from db import audit, execute, query_all, query_one, utc_now_iso


def submit_correction_request(session_id, student_id, requested_status, reason, document_name, requested_by):
    return execute(
        """INSERT INTO correction_requests
           (session_id,student_id,requested_status,reason,document_name,status,requested_by,created_at)
           VALUES (?,?,?,?,?,'Pending',?,?)""",
        (session_id, student_id, requested_status, reason, document_name, requested_by, utc_now_iso()),
    )


def list_correction_requests(department=None, status="Pending"):
    sql = """SELECT cr.*, st.name, st.department, cs.session_date,
                    s.code subject_code, s.name subject_name
             FROM correction_requests cr
             JOIN students st ON st.student_id=cr.student_id
             JOIN class_sessions cs ON cs.id=cr.session_id
             JOIN subjects s ON s.id=cs.subject_id
             WHERE cr.status=?"""
    params=[status]
    if department:
        sql += " AND st.department=?"
        params.append(department)
    sql += " ORDER BY cr.created_at DESC"
    return query_all(sql, params)


def review_correction(request_id, reviewer_id, decision, note=""):
    req = query_one("SELECT * FROM correction_requests WHERE id=?", (request_id,))
    if not req:
        raise ValueError("Correction request not found.")
    if req["status"] != "Pending":
        raise ValueError("Correction request has already been reviewed.")
    execute(
        """UPDATE correction_requests
           SET status=?, reviewed_by=?, review_note=?, reviewed_at=?
           WHERE id=?""",
        (decision, reviewer_id, note, utc_now_iso(), request_id),
    )
    if decision == "Approved":
        execute(
            """INSERT INTO attendance_records(session_id,student_id,status,marked_at,source)
               VALUES (?,?,?,?,?)
               ON CONFLICT(session_id,student_id)
               DO UPDATE SET status=excluded.status, marked_at=excluded.marked_at, source='Correction'""",
            (req["session_id"], req["student_id"], req["requested_status"], utc_now_iso(), "Correction"),
        )
    audit(reviewer_id, f"{decision.lower()}_correction", "correction_request", request_id, {"note": note})
    return True


def submit_condonation_request(student_id, subject_id, reason, document_name, requested_by):
    return execute(
        """INSERT INTO condonation_requests
           (student_id,subject_id,reason,document_name,status,requested_by,created_at)
           VALUES (?,?,?,?, 'Pending',?,?)""",
        (student_id, subject_id, reason, document_name, requested_by, utc_now_iso()),
    )


def list_condonation_requests(department=None, status="Pending"):
    sql = """SELECT cr.*, st.name, st.department,
                    s.code subject_code, s.name subject_name
             FROM condonation_requests cr
             JOIN students st ON st.student_id=cr.student_id
             JOIN subjects s ON s.id=cr.subject_id
             WHERE cr.status=?"""
    params=[status]
    if department:
        sql += " AND st.department=?"
        params.append(department)
    sql += " ORDER BY cr.created_at DESC"
    return query_all(sql, params)


def review_condonation(request_id, reviewer_id, decision, note=""):
    req = query_one("SELECT * FROM condonation_requests WHERE id=?", (request_id,))
    if not req:
        raise ValueError("Condonation request not found.")
    if req["status"] != "Pending":
        raise ValueError("Condonation request has already been reviewed.")
    execute(
        """UPDATE condonation_requests
           SET status=?, reviewed_by=?, review_note=?, reviewed_at=?
           WHERE id=?""",
        (decision, reviewer_id, note, utc_now_iso(), request_id),
    )
    audit(reviewer_id, f"{decision.lower()}_condonation", "condonation_request", request_id, {"note": note})
    return True
