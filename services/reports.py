import pandas as pd
from db import query_all


def attendance_history(student_id, subject_id=None, limit=120):
    sql = """SELECT cs.session_date as Date, s.code as Subject, s.name as SubjectName,
                    COALESCE(ar.status,'Absent') as Status,
                    ar.marked_at as MarkedAt,
                    COALESCE(ar.source,'Session close fallback') as Source
             FROM class_sessions cs
             JOIN subjects s ON s.id=cs.subject_id
             JOIN enrollments e ON e.subject_id=s.id AND e.student_id=?
             LEFT JOIN attendance_records ar
               ON ar.session_id=cs.id AND ar.student_id=?
             WHERE cs.status <> 'cancelled'"""
    params = [student_id, student_id]
    if subject_id:
        sql += " AND s.id=?"
        params.append(subject_id)
    sql += " ORDER BY cs.session_date DESC LIMIT ?"
    params.append(limit)
    return pd.DataFrame(query_all(sql, params))


def faculty_session_report(faculty_id, days=30):
    return pd.DataFrame(
        query_all(
            """SELECT cs.session_date Date, s.code Subject, s.name SubjectName,
                      COUNT(DISTINCT e.student_id) Roster,
                      SUM(CASE WHEN ar.status='Present' THEN 1 ELSE 0 END) Present,
                      ROUND(100.0 * SUM(CASE WHEN ar.status='Present' THEN 1 ELSE 0 END) /
                            NULLIF(COUNT(DISTINCT e.student_id),0),1) AttendancePct
               FROM class_sessions cs
               JOIN subjects s ON s.id=cs.subject_id
               JOIN enrollments e ON e.subject_id=s.id
               LEFT JOIN attendance_records ar
                 ON ar.session_id=cs.id AND ar.student_id=e.student_id
               WHERE cs.created_by=? AND cs.status <> 'cancelled'
                 AND date(cs.session_date) >= date('now', ?)
               GROUP BY cs.id
               ORDER BY cs.session_date DESC""",
            (faculty_id, f"-{days} days"),
        )
    )
