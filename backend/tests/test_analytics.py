"""Phase 5 tests: shift-aware, leave/holiday-aware analytics (real data only)."""

import csv
import io
from datetime import time, timedelta

from app.core.time_utils import now_local
from app.models import Attendance, LeaveRequest, User
from app.services import analytics as svc

TODAY = now_local().date()


class _Rec:
    """Minimal stand-in for the Attendance model in pure-function tests."""

    def __init__(self, user_id, date, time_in=None, status="present", is_late=None):
        self.user_id = user_id
        self.date = date
        self.time_in = time_in
        self.status = status
        self.is_late = is_late


class _User:
    def __init__(self, id, name="User", department=None):
        self.id = id
        self.full_name = name
        self.department = department


# ── Shift-aware punctuality ──────────────────────────────────────────────────


def test_is_late_prefers_shift_flag():
    # The is_late flag was computed at mark time from the user's shift —
    # it wins even when the raw clock time looks early/late vs 09:00.
    assert svc._is_late(_Rec(1, TODAY, time(8, 0), is_late=True)) is True
    assert svc._is_late(_Rec(1, TODAY, time(9, 30), is_late=False)) is False
    # No shift (flag NULL) → legacy 09:00 fallback.
    assert svc._is_late(_Rec(1, TODAY, time(9, 30), is_late=None)) is True
    assert svc._is_late(_Rec(1, TODAY, time(8, 59), is_late=None)) is False
    # No clock-in → never late.
    assert svc._is_late(_Rec(1, TODAY, None, status="absent")) is False


def test_live_stats_uses_flag_for_punctuality():
    users = [_User(1), _User(2)]
    # Shift worker clocked in "late" vs 09:00 but on time for their shift.
    records = [_Rec(1, TODAY, time(9, 30), is_late=False)]
    stats = svc.live_stats(users, records)
    assert stats["lateToday"] == 0
    assert stats["onTimeToday"] == 1
    assert stats["punctualityRate"] == 100.0


# ── Leave/holiday-aware denominators ─────────────────────────────────────────


def test_live_stats_excludes_approved_leave():
    users = [_User(1), _User(2), _User(3)]
    records = [
        _Rec(1, TODAY, time(8, 0), is_late=False),
        _Rec(2, TODAY, None, status="absent"),
    ]
    stats = svc.live_stats(users, records, on_leave_ids={3})
    assert stats["onLeaveToday"] == 1
    assert stats["expectedToday"] == 2
    # User 3 is on approved leave → not counted as absent.
    assert stats["absentToday"] == 1  # user 2 expected but missing
    assert stats["attendanceRate"] == 50.0  # 1 present of 2 expected


def test_live_stats_holiday_nobody_expected():
    users = [_User(1), _User(2)]
    stats = svc.live_stats(users, [], is_holiday=True)
    assert stats["holidayToday"] is True
    assert stats["expectedToday"] == 0
    assert stats["absentToday"] == 0  # nobody is expected on a holiday
    assert stats["attendanceRate"] == 0


def test_department_breakdown_excludes_on_leave():
    users = [_User(1, "A", "Eng"), _User(2, "B", "Eng"), _User(3, "C", "HR")]
    records = [_Rec(1, TODAY, time(8, 0), is_late=False)]
    out = svc.department_breakdown(users, records, on_leave_ids={2})
    by_name = {d["name"]: d for d in out}
    assert by_name["Eng"]["total"] == 1  # user 2 on leave, excluded
    assert by_name["Eng"]["present"] == 1
    assert by_name["Eng"]["attendanceRate"] == 100.0
    assert by_name["HR"]["total"] == 1


def test_daily_trends_leave_and_holiday_flags():
    d0 = TODAY - timedelta(days=2)
    d1 = TODAY - timedelta(days=1)
    d2 = TODAY

    users_total = 2
    records = [
        _Rec(1, d0, time(8, 0), is_late=False),
        _Rec(1, d1, time(8, 0), is_late=False),
        _Rec(1, d2, time(8, 0), is_late=False),
    ]
    holidays = {d0: "Founders Day"}
    leaves = LeaveRequest(
        user_id=2, start_date=d1, end_date=d1, leave_type="annual", status="approved"
    )
    leave_map = svc.on_leave_by_date([leaves])

    rows = svc.daily_trends(records, d0, d2, users_total, leave_map, holidays)
    assert len(rows) == 3

    holiday_row = rows[0]
    assert holiday_row["holiday"] is True
    assert holiday_row["holidayName"] == "Founders Day"
    assert holiday_row["expected"] == 0
    assert holiday_row["attendance"] == 0  # flagged, not a scored 0%

    leave_row = rows[1]
    assert leave_row["holiday"] is False
    assert leave_row["expected"] == 1  # user 2 on approved leave
    assert leave_row["attendance"] == 100.0  # user 1 present of 1 expected

    normal_row = rows[2]
    assert normal_row["expected"] == 2
    assert normal_row["attendance"] == 50.0


def test_weekly_patterns_excludes_holidays_from_denominator():
    records = [_Rec(1, TODAY, time(8, 0), is_late=False)]

    without_holiday = svc.weekly_patterns(records, TODAY, TODAY, 2)
    idx = TODAY.weekday()
    assert without_holiday[idx]["attendance"] == 50.0  # 1 of 2

    with_holiday = svc.weekly_patterns(records, TODAY, TODAY, 2, holidays={TODAY: "Day Off"})
    assert with_holiday[idx]["attendance"] == 0  # nobody expected → no score


def test_on_leave_by_date_spans_range():
    req = LeaveRequest(
        user_id=7,
        start_date=TODAY - timedelta(days=1),
        end_date=TODAY + timedelta(days=1),
        leave_type="annual",
        status="approved",
    )
    mapping = svc.on_leave_by_date([req])
    assert mapping[TODAY - timedelta(days=1)] == {7}
    assert mapping[TODAY] == {7}
    assert mapping[TODAY + timedelta(days=1)] == {7}
    assert (TODAY + timedelta(days=2)) not in mapping


# ── Anomalies / recommendations / report rate ────────────────────────────────


def test_anomaly_date_is_latest_record_even_when_unsorted():
    users = [_User(1, "Low One")]
    dates = [TODAY - timedelta(days=d) for d in (5, 1, 4, 0, 3, 2)]
    # Query order is arbitrary — feed the rows deliberately unsorted.
    records = [
        _Rec(1, dates[0], None, status="absent"),
        _Rec(1, dates[1], None, status="absent"),
        _Rec(1, dates[2], time(8, 0)),
        _Rec(1, dates[3], None, status="absent"),
        _Rec(1, dates[4], time(8, 0)),
        _Rec(1, dates[5], None, status="absent"),
    ]
    anomalies = svc.detect_anomalies(records, users)
    assert len(anomalies) == 1
    assert anomalies[0]["date"] == TODAY.strftime("%b %d")


def test_recommendations_respect_shift_flag():
    users = [_User(1)]
    # After 09:15 by the clock, but the shift flag says on time → no warning.
    on_time = [_Rec(1, TODAY - timedelta(days=i), time(9, 30), is_late=False) for i in range(4)]
    assert not any(
        r["type"] == "punctuality" for r in svc.recommendations(on_time, users)
    )

    # Flagged late (shift start earlier than 09:00) → punctuality warning.
    late = [_Rec(1, TODAY - timedelta(days=i), time(8, 0), is_late=True) for i in range(4)]
    recs = svc.recommendations(late, users)
    assert any(r["type"] == "punctuality" for r in recs)


def test_average_daily_rate_excludes_days_without_expected_people():
    daily = [
        {"attendance": 100.0, "expected": 2},
        {"attendance": 0.0, "expected": 0},  # holiday / all on leave
        {"attendance": 50.0, "expected": 2},
    ]
    assert svc.average_daily_rate(daily) == 75.0
    assert svc.average_daily_rate([{"attendance": 0.0, "expected": 0}]) == 0.0
    assert svc.average_daily_rate([]) == 0.0


# ── Endpoint tests ───────────────────────────────────────────────────────────


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_dashboard_requires_admin(client, user_token, admin_token):
    denied = await client.get("/analytics/dashboard", headers=_auth(user_token))
    assert denied.status_code == 403

    resp = await client.get("/analytics/dashboard", headers=_auth(admin_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Original contract keys must remain present.
    for key in (
        "liveStats",
        "departments",
        "dailyTrends",
        "weeklyStats",
        "userStats",
        "anomalies",
        "period",
        "generatedAt",
    ):
        assert key in body, f"missing {key}"
    # Additive Phase 5 context keys.
    for key in ("onLeaveToday", "expectedToday", "holidayToday"):
        assert key in body["liveStats"], f"missing liveStats.{key}"
    for key in ("expected", "holiday", "holidayName"):
        assert key in body["dailyTrends"][0], f"missing dailyTrends.{key}"


async def test_dashboard_excludes_approved_leave(client, admin_token, user_token, db_session):
    user = db_session.query(User).filter(User.email == "user@test.com").first()
    assert user is not None, "user fixture missing"
    db_session.add(
        LeaveRequest(
            user_id=user.id,
            start_date=TODAY,
            end_date=TODAY,
            leave_type="annual",
            status="approved",
        )
    )
    db_session.commit()

    resp = await client.get(
        "/analytics/dashboard", params={"period": "day"}, headers=_auth(admin_token)
    )
    assert resp.status_code == 200, resp.text
    live = resp.json()["liveStats"]
    assert live["onLeaveToday"] == 1
    assert live["expectedToday"] == live["totalEmployees"] - 1
    # Nobody present; the on-leave user is not "absent".
    assert live["absentToday"] == live["expectedToday"]
    # The leave user's department total also excludes them: the sum of all
    # department totals equals the expected headcount.
    depts = resp.json()["departments"]
    assert sum(d["total"] for d in depts) == live["expectedToday"]


async def test_dashboard_flags_holiday(client, admin_token):
    created = await client.post(
        "/admin/holidays",
        json={"date": TODAY.isoformat(), "name": "Founders Day"},
        headers=_auth(admin_token),
    )
    assert created.status_code == 200, created.text

    resp = await client.get(
        "/analytics/dashboard", params={"period": "day"}, headers=_auth(admin_token)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    live = body["liveStats"]
    assert live["holidayToday"] is True
    assert live["expectedToday"] == 0
    assert live["absentToday"] == 0

    today_row = body["dailyTrends"][-1]
    assert today_row["holiday"] is True
    assert today_row["holidayName"] == "Founders Day"
    assert today_row["expected"] == 0


async def test_anomalies_parameter_validation(client, admin_token):
    for params in ({"days": 0}, {"days": 367}, {"severity": "bogus"}):
        resp = await client.get("/analytics/anomalies", params=params, headers=_auth(admin_token))
        assert resp.status_code == 422, f"{params} should be rejected"

    ok = await client.get("/analytics/anomalies", headers=_auth(admin_token))
    assert ok.status_code == 200
    body = ok.json()
    assert set(body) == {"anomalies", "total", "period", "severityFilter"}

    high = await client.get(
        "/analytics/anomalies", params={"severity": "high"}, headers=_auth(admin_token)
    )
    assert high.status_code == 200


async def test_export_csv_is_parseable(client, admin_token):
    resp = await client.get(
        "/analytics/export", params={"format": "csv", "period": "day"}, headers=_auth(admin_token)
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")

    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == ["metric", "value"]
    metrics = {row[0] for row in rows if len(row) == 2}
    for expected in (
        "total_employees",
        "attendance_rate_percent",
        "expected_today",
        "on_leave_today",
        "holiday_today",
    ):
        assert expected in metrics, f"missing {expected}"
    # Every row must be exactly two columns (quoting integrity).
    assert all(len(row) == 2 for row in rows)


async def test_automated_report_rate_is_true_attendance(
    client, admin_token, user_token, db_session
):
    users = db_session.query(User).all()
    assert len(users) == 2, "expected admin + user fixtures"
    present_id = users[0].id
    absent_id = users[1].id
    db_session.add(
        Attendance(
            user_id=present_id, date=TODAY, time_in=time(8, 0), status="present", is_late=False
        )
    )
    db_session.add(
        Attendance(user_id=absent_id, date=TODAY, time_in=None, status="absent")
    )
    db_session.commit()

    resp = await client.get(
        "/analytics/reports/automated",
        params={"report_type": "daily"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary"]["totalEmployees"] == 2
    # 1 of 2 expected present today → 50.0, not "users present at least once".
    assert body["summary"]["attendanceRate"] == 50.0
    assert "topPerformers" in body and "recommendations" in body


async def test_dashboard_and_report_with_no_data(client, admin_token):
    resp = await client.get(
        "/analytics/dashboard", params={"period": "day"}, headers=_auth(admin_token)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["liveStats"]["currentlyPresent"] == 0
    assert all(row["attendance"] == 0 for row in body["dailyTrends"])
    assert all(row["expected"] >= 0 for row in body["dailyTrends"])

    report = await client.get(
        "/analytics/reports/automated", headers=_auth(admin_token)
    )
    assert report.status_code == 200, report.text
    # With data, users exist but nobody was present: rate 0.0, not a crash.
    assert report.json()["summary"]["attendanceRate"] == 0.0
