from collections import Counter
from db import query_all


def detect_session_anomalies(session_id):
    records = query_all(
        """SELECT ar.student_id, ar.marked_at, ar.device_id, ar.source,
                  st.name
           FROM attendance_records ar
           JOIN students st ON st.student_id=ar.student_id
           WHERE ar.session_id=?""",
        (session_id,),
    )
    attempts = query_all(
        """SELECT * FROM attendance_attempts
           WHERE session_id=? ORDER BY attempted_at""",
        (session_id,),
    )
    findings = []

    devices = Counter(r["device_id"] for r in records if r["device_id"])
    for device_id, count in devices.items():
        student_ids = [r["student_id"] for r in records if r["device_id"] == device_id]
        if count > 1 and len(set(student_ids)) > 1:
            findings.append({
                "severity": "High",
                "type": "Shared device identity",
                "evidence": f"One registered device identity was used by {len(set(student_ids))} students.",
            })

    token_use = {}
    for r in records:
        if r.get("token_id"):
            token_use.setdefault(r["token_id"], set()).add(r["student_id"])
    for token_id, student_ids in token_use.items():
        if len(student_ids) > 1:
            findings.append({
                "severity": "High",
                "type": "Token reused across identities",
                "evidence": f"The same short-lived token was accepted for {len(student_ids)} students.",
            })

    accepted = sorted([r["marked_at"] for r in records if r["source"] == "Dynamic QR"])
    if len(accepted) >= 8:
        from datetime import datetime
        parsed = [datetime.fromisoformat(x) for x in accepted]
        for i in range(len(parsed) - 7):
            window = (parsed[i + 7] - parsed[i]).total_seconds()
            if window <= 5:
                findings.append({
                    "severity": "Medium",
                    "type": "Abnormally fast check-in burst",
                    "evidence": f"{i + 8} QR check-ins occurred within {window:.1f} seconds.",
                })
                break

    failed = [a for a in attempts if a["status"] == "Rejected"]
    reasons = Counter(a["reason"] for a in failed)
    for reason, count in reasons.items():
        if count >= 3:
            findings.append({
                "severity": "Medium",
                "type": "Repeated rejected attempts",
                "evidence": f"{count} rejected attempts share the reason: {reason}.",
            })

    duplicate_attempts = [a for a in attempts if a["reason"] == "Duplicate attendance"]
    if duplicate_attempts:
        findings.append({
            "severity": "Low",
            "type": "Duplicate attendance attempts",
            "evidence": f"{len(duplicate_attempts)} duplicate submission attempts were blocked.",
        })

    return findings


def session_trust_label(findings):
    if any(f["severity"] == "High" for f in findings):
        return "Review required"
    if any(f["severity"] == "Medium" for f in findings):
        return "Watch"
    return "No material anomaly detected"
