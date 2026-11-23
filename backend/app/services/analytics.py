"""
Attendance analytics computed strictly from real records.

Data model available: Attendance(user_id, date, time_in, status, is_late),
User(department), plus the scheduling domain from Phase 2 (approved
LeaveRequest ranges and Holiday dates). Every metric below is derived only
from those facts — no simulated, random, or fabricated values.

Definitions:
  * Punctuality is shift-aware: Attendance.is_late is computed at mark time
    from the user's shift (start + grace minutes), so it is preferred. Rows
    from users without a shift have is_late = NULL and fall back to the
    legacy WORK_START (09:00) rule.
  * Attendance rate = distinct present users / expected users, where
    expected excludes users on approved leave; on a holiday nobody is
    expected (expected = 0), so the day is flagged rather than scored 0%.
  * Streak = consecutive calendar days present, counting back from a user's
    most recent present day.
"""

from collections import Counter, defaultdict
from datetime import time, timedelta

from app.core.time_utils import now_local

# Legacy on-time boundary, still used for users with no shift (is_late NULL).
WORK_START = time(9, 0)


def _is_late(record) -> bool:
    """Shift-aware lateness for one attendance row.

    Prefers the is_late flag written at mark time (encodes the user's shift
    start + grace). Falls back to the legacy 09:00 rule when the flag is NULL
    (no shift assigned). Rows without a clock-in are never "late".
    """
    if record.time_in is None:
        return False
    if record.is_late is not None:
        return bool(record.is_late)
    return record.time_in > WORK_START


def on_leave_by_date(leaves) -> dict:
    """Map each calendar date in the leave ranges to the user ids on leave."""
    out = defaultdict(set)
    for req in leaves:
        day = req.start_date
        while day <= req.end_date:
            out[day].add(req.user_id)
            day += timedelta(days=1)
    return out


def _avg_arrival(times) -> str:
    if not times:
        return "N/A"
    secs = sum(t.hour * 3600 + t.minute * 60 + t.second for t in times) / len(times)
    return f"{int(secs // 3600):02d}:{int((secs % 3600) // 60):02d}"


def _format_hour(hour: int) -> str:
    h12 = hour % 12 or 12
    return f"{h12} {'AM' if hour < 12 else 'PM'}"


def live_stats(users: list, records: list, *, on_leave_ids=frozenset(), is_holiday: bool = False) -> dict:
    """Today's snapshot, excluding users not expected in today (approved
    leave, and everyone when today is a holiday)."""
    today = now_local().date()
    today_present = [r for r in records if r.date == today and r.status == "present"]
    present_ids = {r.user_id for r in today_present}
    times = [r.time_in for r in today_present if r.time_in]
    late = sum(1 for r in today_present if _is_late(r))
    on_time = sum(1 for r in today_present if r.time_in is not None and not _is_late(r))

    total = len(users)
    present = len(present_ids)
    # Nobody is expected on a holiday; otherwise expected = staff minus those
    # on approved leave.
    expected = 0 if is_holiday else max(0, total - len(on_leave_ids))
    # "Absent" means "expected but not here" — leave/holiday-covered staff
    # are not counted against attendance.
    absent = max(0, expected - present)

    return {
        "totalEmployees": total,
        "currentlyPresent": present,
        "onTimeToday": on_time,
        "lateToday": late,
        "absentToday": absent,
        # Rate over people expected in today (leave/holiday excluded), so it
        # agrees with absentToday; without leave/holiday expected == total.
        "attendanceRate": round(present / expected * 100, 1) if expected else 0,
        "punctualityRate": round(on_time / present * 100, 1) if present else 0,
        "averageArrival": _avg_arrival(times),
        "peakHour": _format_hour(Counter(t.hour for t in times).most_common(1)[0][0]) if times else "N/A",
        # Additive context (Phase 5) so callers can explain a low rate.
        "onLeaveToday": len(on_leave_ids),
        "expectedToday": expected,
        "holidayToday": is_holiday,
    }


def department_breakdown(users: list, records: list, *, on_leave_ids=frozenset()) -> list:
    """Per-department present/total for today. Users on approved leave are
    excluded from their department's total (they are not expected in)."""
    today = now_local().date()
    present_ids = {r.user_id for r in records if r.date == today and r.status == "present"}

    totals = defaultdict(int)
    present = defaultdict(int)
    for u in users:
        if u.id in on_leave_ids:
            continue
        dept = u.department or "Unassigned"
        totals[dept] += 1
        if u.id in present_ids:
            present[dept] += 1

    return [
        {
            "name": dept,
            "present": present[dept],
            "total": totals[dept],
            "attendanceRate": round(present[dept] / totals[dept] * 100, 1) if totals[dept] else 0,
        }
        for dept in sorted(totals)
    ]


def daily_trends(
    records: list,
    start_date,
    end_date,
    total_users: int,
    on_leave_by_date=None,
    holidays=None,
) -> list:
    """Per-day attendance % and on-time % across the period.

    Denominators exclude users on approved leave that day; holiday days are
    expected-empty and carry holiday/holidayName flags with expected = 0 so
    consumers can gap them instead of plotting a false 0%.
    """
    on_leave_by_date = on_leave_by_date or {}
    holidays = holidays or {}

    by_date = defaultdict(list)
    for r in records:
        if r.status == "present":
            by_date[r.date].append(r)

    out = []
    day = start_date
    while day <= end_date:
        recs = by_date.get(day, [])
        present = len({r.user_id for r in recs})
        on_time = sum(1 for r in recs if r.time_in is not None and not _is_late(r))
        on_leave = on_leave_by_date.get(day, frozenset())
        is_holiday = day in holidays
        expected = 0 if is_holiday else max(0, total_users - len(on_leave))
        out.append({
            "date": day.strftime("%b %d"),
            "attendance": round(present / expected * 100, 1) if expected else 0,
            "onTime": round(on_time / present * 100, 1) if present else 0,
            # Additive context (Phase 5).
            "expected": expected,
            "holiday": is_holiday,
            "holidayName": holidays.get(day) if is_holiday else None,
        })
        day += timedelta(days=1)
    return out


def weekly_patterns(
    records: list,
    start_date,
    end_date,
    total_users: int,
    on_leave_by_date=None,
    holidays=None,
) -> list:
    """Average attendance % and late-arrival counts by weekday over the
    period. Holiday dates and leave-covered users are excluded from the
    denominators so an org-wide day off cannot drag a weekday down."""
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    on_leave_by_date = on_leave_by_date or {}
    holidays = holidays or {}

    denom = [0] * 7
    day = start_date
    while day <= end_date:
        if day not in holidays:
            on_leave = on_leave_by_date.get(day, frozenset())
            denom[day.weekday()] += max(0, total_users - len(on_leave))
        day += timedelta(days=1)

    present_pairs = defaultdict(set)  # weekday -> {(user_id, date)}
    late_counts = [0] * 7
    for r in records:
        if r.status == "present":
            wd = r.date.weekday()
            present_pairs[wd].add((r.user_id, r.date))
            if _is_late(r):
                late_counts[wd] += 1

    out = []
    for i, name in enumerate(names):
        present_count = len(present_pairs.get(i, set()))
        out.append({
            "name": name,
            "attendance": round(present_count / denom[i] * 100, 1) if denom[i] else 0,
            "lateArrivals": late_counts[i],
        })
    return out


def user_performance(users: list, records: list) -> list:
    """Top users by attendance % over the period (with real current streak)."""
    by_user = defaultdict(list)
    for r in records:
        by_user[r.user_id].append(r)

    users_by_id = {u.id: u for u in users}
    out = []
    for uid, recs in by_user.items():
        user = users_by_id.get(uid)
        if not user:
            continue

        present_dates = sorted({r.date for r in recs if r.status == "present"})
        total = len(recs)
        present = len(present_dates)

        streak = 0
        if present_dates:
            present_set = set(present_dates)
            cursor = present_dates[-1]
            while cursor in present_set:
                streak += 1
                cursor -= timedelta(days=1)

        out.append({
            "name": user.full_name,
            "department": user.department or "Unassigned",
            "attendance": round(present / total * 100, 1) if total else 0,
            "presentDays": present,
            "streak": streak,
        })

    out.sort(key=lambda x: (x["attendance"], x["streak"]), reverse=True)
    return out[:5]


def detect_anomalies(records: list, users: list) -> list:
    """Flag users whose attendance rate over the period is below 60%."""
    anomalies = []
    by_user = defaultdict(list)
    for r in records:
        by_user[r.user_id].append(r)

    users_by_id = {u.id: u for u in users}
    for uid, recs in by_user.items():
        user = users_by_id.get(uid)
        if not user:
            continue
        present = [r for r in recs if r.status == "present"]
        if len(recs) > 5 and len(present) / len(recs) < 0.6:
            # The query has no ORDER BY — sort explicitly so "date" is the
            # user's most recent record, not an arbitrary one.
            latest = max(r.date for r in recs)
            anomalies.append({
                "type": "low_attendance",
                "user": user.full_name,
                "description": f"Attendance rate below 60% ({len(present)}/{len(recs)} days)",
                "severity": "high",
                "date": latest.strftime("%b %d"),
            })
    return anomalies


def recommendations(records: list, users: list) -> list:
    """Actionable recommendations derived from real attendance/punctuality."""
    out = []
    present = [r for r in records if r.status == "present"]
    rate = len({r.user_id for r in present}) / max(len(users), 1) * 100
    if rate < 80:
        out.append({
            "type": "attendance",
            "priority": "high",
            "title": "Low Overall Attendance",
            "description": f"Attendance rate is {rate:.1f}%. Consider attendance incentives.",
        })

    late = [r for r in present if _is_late(r)]
    if present and len(late) > len(present) * 0.3:
        out.append({
            "type": "punctuality",
            "priority": "medium",
            "title": "Punctuality Issues",
            "description": f"{len(late)} late arrivals detected. Consider flexible timing.",
        })
    return out


def average_daily_rate(daily: list) -> float:
    """Mean of the per-day attendance rates for days where anyone was
    expected (excludes holidays and all-on-leave days). Used by the
    automated report so its attendanceRate is a true attendance rate."""
    rates = [d["attendance"] for d in daily if d.get("expected", 0) > 0]
    if not rates:
        return 0.0
    return round(sum(rates) / len(rates), 1)
