from datetime import date, timedelta
from db import execute, query_all, query_one, utc_now_iso


def create_intervention(student_id, subject_id, trigger_type, recommendation, owner_role="faculty", due_days=7):
    existing = query_one(
        """SELECT id FROM interventions
           WHERE student_id=? AND subject_id IS ? AND trigger_type=? AND status <> 'Resolved'""",
        (student_id, subject_id, trigger_type),
    )
    if existing:
        return existing["id"]
    due = (date.today() + timedelta(days=due_days)).isoformat()
    return execute(
        """INSERT INTO interventions(student_id,subject_id,trigger_type,recommendation,owner_role,status,due_date,created_at)
           VALUES (?,?,?,?,?,'Open',?,?)""",
        (student_id, subject_id, trigger_type, recommendation, owner_role, due, utc_now_iso()),
    )


def list_interventions(department=None, open_only=True):
    sql = """SELECT i.*, st.name, st.department, s.code, s.name as subject_name
             FROM interventions i
             JOIN students st ON st.student_id=i.student_id
             LEFT JOIN subjects s ON s.id=i.subject_id
             WHERE 1=1"""
    params = []
    if department:
        sql += " AND st.department=?"
        params.append(department)
    if open_only:
        sql += " AND i.status <> 'Resolved'"
    sql += " ORDER BY CASE i.status WHEN 'Open' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END, i.created_at DESC"
    return query_all(sql, params)


def update_intervention(intervention_id, status, notes=None):
    execute(
        """UPDATE interventions
           SET status=?, notes=COALESCE(?,notes),
               resolved_at=CASE WHEN ?='Resolved' THEN ? ELSE resolved_at END
           WHERE id=?""",
        (status, notes, status, utc_now_iso() if status == "Resolved" else None, intervention_id),
    )
