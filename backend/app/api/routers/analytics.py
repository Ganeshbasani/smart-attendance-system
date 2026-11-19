"""Admin analytics, reporting, and anomaly endpoints (real data only)."""

import csv
import io
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api import deps
from app.core.time_utils import now_local
from app.db.session import get_db
from app.models import Attendance, Holiday, LeaveRequest, User
from app.services import analytics as svc

logger = logging.getLogger("smart_attendance.analytics")

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _period_start(period: str, today: datetime) -> datetime:
    if period == "day":
        return today.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        return today - timedelta(days=30)
    if period == "quarter":
        return today - timedelta(days=90)
    return today - timedelta(days=7)  # default: week


def _scheduling_context(start_date, end_date, db: Session):
    """Approved-leave map and holiday names for the period.

    Analytics must not count users who are not expected (approved leave) or
    org-wide days off as attendance failures — both come from the Phase 2
    scheduling domain.
    """
    leaves = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        .all()
    )
    holidays = {
        h.date: h.name
        for h in db.query(Holiday)
        .filter(Holiday.date >= start_date, Holiday.date <= end_date)
        .all()
    }
    return svc.on_leave_by_date(leaves), holidays


def _build_dashboard(period: str, db: Session) -> dict:
    today = now_local()
    start_date = _period_start(period, today).date()
    end_date = today.date()

    records = db.query(Attendance).filter(Attendance.date >= start_date).all()
    users = db.query(User).all()
    total_users = len(users)
    on_leave_by_date, holidays = _scheduling_context(start_date, end_date, db)
    today_leave = on_leave_by_date.get(end_date, frozenset())

    return {
        "liveStats": svc.live_stats(
            users, records, on_leave_ids=today_leave, is_holiday=end_date in holidays
        ),
        "departments": svc.department_breakdown(users, records, on_leave_ids=today_leave),
        "dailyTrends": svc.daily_trends(
            records, start_date, end_date, total_users, on_leave_by_date, holidays
        ),
        "weeklyStats": svc.weekly_patterns(
            records, start_date, end_date, total_users, on_leave_by_date, holidays
        ),
        "userStats": svc.user_performance(users, records),
        "anomalies": svc.detect_anomalies(records, users),
        "period": period,
        "generatedAt": today.isoformat(),
    }


@router.get("/dashboard")
async def get_analytics_dashboard(
    period: str = "week",
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    try:
        return _build_dashboard(period, db)
    except Exception:
        logger.exception("Analytics calculation failed")
        raise HTTPException(status_code=500, detail="Analytics calculation failed.")


@router.get("/export")
async def export_analytics_data(
    format: str = "csv",
    period: str = "week",
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    try:
        data = _build_dashboard(period, db)
        live = data["liveStats"]

        if format.lower() == "csv":
            # stdlib csv writer: values are quoted correctly, so a future
            # metric containing a comma cannot break the row structure.
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(("metric", "value"))
            writer.writerow(("period", period))
            writer.writerow(("generated_at", data["generatedAt"]))
            writer.writerow(("total_employees", live["totalEmployees"]))
            writer.writerow(("currently_present", live["currentlyPresent"]))
            writer.writerow(("attendance_rate_percent", live["attendanceRate"]))
            writer.writerow(("on_time_today", live["onTimeToday"]))
            writer.writerow(("late_today", live["lateToday"]))
            writer.writerow(("absent_today", live["absentToday"]))
            writer.writerow(("punctuality_rate_percent", live["punctualityRate"]))
            writer.writerow(("average_arrival", live["averageArrival"]))
            writer.writerow(("expected_today", live["expectedToday"]))
            writer.writerow(("on_leave_today", live["onLeaveToday"]))
            writer.writerow(("holiday_today", str(live["holidayToday"]).lower()))
            return Response(
                content=buf.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=analytics-{period}.csv"},
            )

        return data
    except Exception:
        logger.exception("Analytics export failed")
        raise HTTPException(status_code=500, detail="Export failed.")


@router.get("/reports/automated")
async def generate_automated_report(
    report_type: str = "weekly",
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    try:
        today = now_local()
        period_map = {"daily": "day", "monthly": "month"}
        period = period_map.get(report_type, "week")
        title = {"daily": "Daily", "monthly": "Monthly"}.get(report_type, "Weekly") + " Attendance Report"

        start_date = _period_start(period, today).date()
        end_date = today.date()
        records = db.query(Attendance).filter(Attendance.date >= start_date).all()
        users = db.query(User).all()
        on_leave_by_date, holidays = _scheduling_context(start_date, end_date, db)

        daily = svc.daily_trends(
            records, start_date, end_date, len(users), on_leave_by_date, holidays
        )
        # Mean of per-day rates on days where anyone was expected — a real
        # attendance rate, not "users present at least once".
        attendance_rate = svc.average_daily_rate(daily)

        return {
            "title": title,
            "period": report_type,
            "generatedAt": today.isoformat(),
            "summary": {
                "totalEmployees": len(users),
                "totalRecords": len(records),
                "attendanceRate": attendance_rate,
            },
            "recommendations": svc.recommendations(records, users),
            "topPerformers": svc.user_performance(users, records)[:3],
        }
    except Exception:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail="Report generation failed.")


@router.get("/anomalies")
async def get_attendance_anomalies(
    days: int = Query(7, ge=1, le=366),
    severity: str = Query("all", pattern="^(all|high|medium|low)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    try:
        start_date = now_local() - timedelta(days=days)
        records = db.query(Attendance).filter(Attendance.date >= start_date.date()).all()
        users = db.query(User).all()

        anomalies = svc.detect_anomalies(records, users)
        if severity != "all":
            anomalies = [a for a in anomalies if a["severity"] == severity]

        return {
            "anomalies": anomalies,
            "total": len(anomalies),
            "period": f"Last {days} days",
            "severityFilter": severity,
        }
    except Exception:
        logger.exception("Anomaly detection failed")
        raise HTTPException(status_code=500, detail="Anomaly detection failed.")
