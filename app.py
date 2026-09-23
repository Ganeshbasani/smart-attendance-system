import io
import json
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from html import escape

import pandas as pd
import plotly.express as px
import qrcode
import streamlit as st

from auth import hash_password, login_allowed, new_session, record_login_attempt, session_valid, verify_password
from config import DATA_DIR, DB_PATH, PRODUCT_NAME, PRODUCT_TAGLINE, TIMEZONE_NAME
from db import (
    audit,
    get_setting,
    init_db,
    query_all,
    query_one,
    set_setting,
    utc_now_iso,
)
from seed import seed
from services.anomaly import detect_session_anomalies, session_trust_label
from services.attendance_service import (
    get_student_dashboard,
    mark_faculty_attendance,
    session_summary,
    session_token,
    submit_qr_attendance,
)
from services.interventions import create_intervention, list_interventions, update_intervention
from services.notifications import list_notifications, mark_read, refresh_student_notifications
from services.reports import attendance_history, faculty_session_report
from services.risk_engine import explain_risk
from services.workflows import (
    list_condonation_requests,
    list_correction_requests,
    review_condonation,
    review_correction,
    submit_condonation_request,
    submit_correction_request,
)


st.set_page_config(
    page_title=f"{PRODUCT_NAME} | Intelligence Platform",
    page_icon="✓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------
# Production-oriented design system
# ---------------------------
st.markdown(
    """
<style>
:root{
  --bg:#f7f8fa;
  --panel:#ffffff;
  --panel-2:#f2f4f7;
  --border:#e3e7ed;
  --text:#172033;
  --muted:#667085;
  --primary:#1f5eff;
  --primary-soft:#eaf0ff;
  --success:#147a4b;
  --success-soft:#e9f8f0;
  --warning:#9a6400;
  --warning-soft:#fff7e6;
  --danger:#b42318;
  --danger-soft:#fff0ee;
  --shadow:0 6px 24px rgba(16,24,40,.06);
}
.stApp{background:var(--bg);color:var(--text)}
.main .block-container{max-width:1480px;padding-top:1.15rem;padding-bottom:4rem}
#MainMenu,footer{visibility:hidden}
header[data-testid="stHeader"]{background:transparent}
*{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--border)}
section[data-testid="stSidebar"] > div{padding-top:1rem}
.brand{display:flex;align-items:center;gap:11px;padding:8px 8px 18px}
.brand-mark{width:36px;height:36px;border-radius:9px;background:var(--primary);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800}
.brand-title{font-size:17px;font-weight:800;letter-spacing:-.4px}
.brand-sub{font-size:10px;color:#98a2b3;margin-top:2px;letter-spacing:.6px}
.nav-head{font-size:10px;text-transform:uppercase;color:#98a2b3;letter-spacing:1.2px;font-weight:700;margin:16px 8px 7px}
div[data-testid="stSidebar"] div[role="radiogroup"]{gap:3px}
div[data-testid="stSidebar"] div[role="radiogroup"] label{border-radius:8px;padding:8px 9px;border:1px solid transparent}
div[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:#f5f7fa}
div[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"]{background:var(--primary-soft);border-color:#cad7ff}
.sidebar-footer{margin-top:18px;padding:12px;border:1px solid var(--border);border-radius:10px;background:#fbfcfd}
.page-kicker{font-size:10px;text-transform:uppercase;color:#61708a;letter-spacing:1.35px;font-weight:800}
.page-title{font-size:30px;line-height:1.1;font-weight:800;letter-spacing:-.8px;margin-top:5px}
.page-desc{font-size:13px;color:var(--muted);margin:8px 0 20px;max-width:850px}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:11px 13px;background:#fff;border:1px solid var(--border);border-radius:11px;box-shadow:var(--shadow);margin-bottom:20px}
.topbar small{color:#98a2b3;font-size:11px}.topbar strong{font-size:13px}
.profile{display:flex;align-items:center;gap:8px}.avatar{width:29px;height:29px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#eef2f7;color:#344054;font-size:11px;font-weight:800}
.card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:16px;box-shadow:var(--shadow)}
.card-tight{padding:12px}.card-title{font-size:14px;font-weight:750}.card-sub{font-size:11px;color:#98a2b3;margin-top:3px}
.metric{background:#fff;border:1px solid var(--border);border-radius:12px;padding:15px;box-shadow:var(--shadow);min-height:104px}
.metric-label{font-size:11px;color:#667085;font-weight:650}.metric-value{font-size:25px;font-weight:800;letter-spacing:-.5px;margin-top:8px}.metric-note{font-size:10px;color:#98a2b3;margin-top:4px}
.status{display:inline-flex;align-items:center;padding:4px 8px;border-radius:999px;font-size:10px;font-weight:750}
.safe{background:var(--success-soft);color:var(--success)}.watch{background:var(--warning-soft);color:var(--warning)}.risk{background:#fff3dd;color:#975f00}.critical{background:var(--danger-soft);color:var(--danger)}
.signal{padding:9px 10px;border-left:3px solid #d0d5dd;background:#fafbfc;margin:6px 0;border-radius:6px;font-size:12px;color:#475467}
.runway{border:1px solid #dfe5ef;border-radius:14px;background:linear-gradient(180deg,#fff,#fbfcff);padding:18px;box-shadow:var(--shadow)}
.runway-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.runway-value{font-size:33px;font-weight:850;letter-spacing:-1px}.runway-copy{font-size:13px;color:#475467;line-height:1.55;margin-top:5px}
.progress-track{height:8px;background:#eef1f5;border-radius:999px;overflow:hidden;margin:12px 0 8px}.progress-fill{height:100%;background:var(--primary);border-radius:999px}
.notice{border:1px solid #dfe5ef;background:#fcfdff;border-radius:10px;padding:11px 12px;font-size:12px;color:#475467}
.notice strong{color:var(--text)}
.login-wrap{max-width:460px;margin:7vh auto 0}.login-card{background:#fff;border:1px solid var(--border);box-shadow:0 14px 50px rgba(16,24,40,.09);border-radius:16px;padding:28px}
.table-note{font-size:11px;color:#98a2b3;margin-top:5px}
.footer{margin-top:50px;padding-top:15px;border-top:1px solid var(--border);font-size:10px;color:#98a2b3}
@media(max-width:900px){.main .block-container{padding-left:1rem;padding-right:1rem}.page-title{font-size:24px}}
</style>
""",
    unsafe_allow_html=True,
)

init_db()
if not query_one("SELECT student_id FROM students LIMIT 1"):
    seed()

# ---------------------------
# Session helpers
# ---------------------------
defaults = {
    "page": "Overview",
    "auth": None,
    "show_login": True,
    "device_id": secrets.token_urlsafe(18),
    "active_session_id": None,
    "active_token": None,
    "active_token_expires": None,
    "offline_queue": [],
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Stable browser identity is deliberately an opaque token kept in the URL; it is not a hardware fingerprint.
try:
    query_device = st.query_params.get("device")
    if "device_id" not in st.session_state or query_device:
        if not query_device:
            query_device = st.session_state.get("device_id") or secrets.token_urlsafe(18)
            st.query_params["device"] = query_device
        st.session_state.device_id = query_device
except Exception:
    pass


def current_user():
    auth = st.session_state.get("auth")
    if not session_valid(auth):
        st.session_state.auth = None
        return None
    return query_one(
        """SELECT id,username,full_name,role,student_id,department,active
           FROM users WHERE id=? AND active=1""",
        (auth["user_id"],),
    )


def do_login(username, password):
    username = username.strip()
    if not login_allowed(username):
        return "locked"
    user = query_one("SELECT * FROM users WHERE username=? AND active=1", (username,))
    ok = bool(user and verify_password(password, user["password_hash"]))
    record_login_attempt(username, ok)
    if not ok:
        return False
    st.session_state.auth = {"user_id": user["id"], **new_session()}
    audit(user["id"], "login", "user", user["id"])
    return True


def logout():
    user = current_user()
    if user:
        audit(user["id"], "logout", "user", user["id"])
    st.session_state.auth = None
    st.session_state.page = "Overview"
    st.rerun()


def role_nav(role):
    if role == "student":
        return ["Overview", "My Attendance", "Verify Attendance", "Requests", "Notifications"]
    if role == "faculty":
        return ["Overview", "Take Attendance", "Risk Monitor", "Session Review", "Corrections", "Sync Center", "Reports"]
    if role == "hod":
        return ["Overview", "Department Intelligence", "Interventions", "Reports"]
    return ["Overview", "Departments", "Roster", "Users", "Audit Log", "System Health", "Policy"]


def page_header(kicker, title, desc=""):
    st.markdown(f'<div class="page-kicker">{escape(kicker)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{escape(title)}</div>', unsafe_allow_html=True)
    if desc:
        st.markdown(f'<div class="page-desc">{escape(desc)}</div>', unsafe_allow_html=True)


def metric(label, value, note=""):
    st.markdown(
        f'<div class="metric"><div class="metric-label">{escape(str(label))}</div>'
        f'<div class="metric-value">{escape(str(value))}</div>'
        f'<div class="metric-note">{escape(str(note))}</div></div>',
        unsafe_allow_html=True,
    )


def risk_badge(state):
    cls = {"Safe": "safe", "Watch": "watch", "At Risk": "risk", "Critical": "critical"}.get(state, "watch")
    return f'<span class="status {cls}">{escape(state)}</span>'


def runway_card(s):
    required = s["required_future"]
    remaining = s["remaining"]
    next_n = s["next_window"]
    next_need = s["needed_next_window"]
    if remaining:
        if not s["recoverable"]:
            copy = "The current runway cannot mathematically recover to the configured threshold."
        else:
            semester_copy = f"Attend {required} of the remaining {remaining} planned sessions." if required else "The remaining sessions can be missed without crossing the threshold."
            near_copy = f"Near-term: attend {next_need} of the next {next_n}." if next_n else ""
            copy = f"{near_copy} <span style='color:#667085'>{semester_copy}</span>"
    else:
        copy = "No planned sessions remain in this subject."
    st.markdown(
        f"""
        <div class="runway">
          <div class="runway-head">
            <div>
              <div class="card-sub">{escape(s['subject_code'])} · {escape(s['subject_name'])}</div>
              <div class="runway-value">{s['current_pct']:.1f}%</div>
              <div class="runway-copy">{copy}</div>
            </div>
            <div>{risk_badge(s['risk_state'])}</div>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:{min(max(s['current_pct'],0),100)}%"></div></div>
          <div style="display:flex;justify-content:space-between;gap:12px;font-size:10px;color:#667085;">
            <span>{s['attended']} attended · {s['conducted']} conducted</span>
            <span>{s['remaining']} remaining</span>
            <span>Projected {s['projected_pct']:.1f}%</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def qr_png(text):
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def ensure_token(session_id):
    exp = st.session_state.get("active_token_expires")
    tok = st.session_state.get("active_token")
    now = datetime.now(timezone.utc)
    if st.session_state.get("active_session_id") != session_id or not tok or not exp or exp <= now:
        tok, exp = session_token(session_id, ttl_seconds=45)
        st.session_state.active_session_id = session_id
        st.session_state.active_token = tok
        st.session_state.active_token_expires = exp
    return tok, st.session_state.active_token_expires


def render_student_overview(user):
    stats = get_student_dashboard(user["student_id"])
    refresh_student_notifications(user["student_id"], stats)
    states = [s["risk_state"] for s in stats]
    critical = states.count("Critical")
    at_risk = states.count("At Risk")
    overall = {
        "conducted": sum(s["conducted"] for s in stats),
        "attended": sum(s["attended"] for s in stats),
    }
    overall_pct = overall["attended"] / overall["conducted"] * 100 if overall["conducted"] else 0
    page_header("Student workspace", "Know where you stand.", "Attendance intelligence turns your records into a recovery plan before eligibility becomes a last-minute problem.")
    cols = st.columns(4)
    with cols[0]: metric("Overall attendance", f"{overall_pct:.1f}%", "Across enrolled subjects")
    with cols[1]: metric("Subjects needing action", critical + at_risk, "Critical + At Risk")
    with cols[2]: metric("Strong subjects", sum(s["risk_state"]=="Safe" for s in stats), "Currently Safe")
    with cols[3]: metric("Policy threshold", f"{get_setting('attendance_threshold','75')}%", "Institution policy")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.45, 1])
    with left:
        st.markdown('<div class="card-title">Attendance runway</div><div class="card-sub">The next-action view of your attendance, not just a percentage.</div><div style="height:10px"></div>', unsafe_allow_html=True)
        for s in stats:
            runway_card(s)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card"><div class="card-title">What changed?</div><div class="card-sub">Explainable risk signals</div><div style="height:8px"></div>', unsafe_allow_html=True)
        for s in sorted(stats, key=lambda x: (["Critical","At Risk","Watch","Safe"].index(x["risk_state"]), x["current_pct"])):
            st.markdown(
                f'<div style="padding:9px 0;border-bottom:1px solid #eef1f5">'
                f'<div style="display:flex;justify-content:space-between"><strong>{escape(s["subject_code"])}</strong>{risk_badge(s["risk_state"])}</div>'
                f'<div class="table-note">{escape(explain_risk({"state":s["risk_state"],"signals":s["risk_signals"]}, s))}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    if critical or at_risk:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="notice"><strong>Recommended next step:</strong> open My Attendance, focus on the first Critical/At Risk subject, and use its runway requirement. Attendance risk is shown as evidence-backed signals rather than an opaque AI score.</div>',
            unsafe_allow_html=True,
        )


def render_faculty_overview(user):
    page_header("Faculty workspace", "Run the room, not the register.", "Today’s workflow puts session capture first, then surfaces students and sessions that need attention.")
    subjects = query_all("SELECT * FROM subjects WHERE department=? OR department='CSE' ORDER BY code", (user["department"] or "CSE",))
    today_sessions = query_all(
        """SELECT cs.*, s.code, s.name,
                  SUM(CASE WHEN ar.status='Present' THEN 1 ELSE 0 END) Present,
                  COUNT(DISTINCT e.student_id) Roster
           FROM class_sessions cs
           JOIN subjects s ON s.id=cs.subject_id
           JOIN enrollments e ON e.subject_id=s.id
           LEFT JOIN attendance_records ar ON ar.session_id=cs.id AND ar.student_id=e.student_id
           WHERE cs.created_by=? AND cs.session_date=?
           GROUP BY cs.id ORDER BY cs.start_time""",
        (user["id"], date.today().isoformat()),
    )
    pending = len(list_correction_requests(user["department"]))
    cols=st.columns(4)
    with cols[0]: metric("Today’s sessions", len(today_sessions), "Owned by you")
    with cols[1]: metric("Sessions open", sum(s["status"]=="open" for s in today_sessions), "Ready for check-in")
    with cols[2]: metric("Pending corrections", pending, "Human review queue")
    with cols[3]: metric("Subjects available", len(subjects), "Department workspace")
    st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
    a,b=st.columns([1.4,1])
    with a:
        st.markdown('<div class="card"><div class="card-title">Today’s sessions</div><div class="card-sub">Start or continue an attendance session.</div><div style="height:8px"></div>',unsafe_allow_html=True)
        if today_sessions:
            st.dataframe(pd.DataFrame(today_sessions)[["code","name","start_time","end_time","status","Present","Roster"]],use_container_width=True,hide_index=True)
        else:
            st.info("No sessions have been opened today. Use Take Attendance to start one.")
        st.markdown("</div>",unsafe_allow_html=True)
    with b:
        at_risk = []
        for strow in query_all("SELECT student_id,name FROM students WHERE department=?", (user["department"] or "CSE",)):
            for s in get_student_dashboard(strow["student_id"]):
                if s["risk_state"] in ("Critical","At Risk"):
                    at_risk.append((strow["name"],strow["student_id"],s["subject_code"],s["current_pct"],s["risk_state"]))
        st.markdown('<div class="card"><div class="card-title">Students needing attention</div><div class="card-sub">Latest risk state, by subject.</div><div style="height:8px"></div>',unsafe_allow_html=True)
        if at_risk:
            st.dataframe(pd.DataFrame(at_risk[:12], columns=["Student","ID","Subject","Attendance %","Risk"]),use_container_width=True,hide_index=True)
        else:
            st.success("No Critical or At Risk subjects were detected in the current data.")
        st.markdown("</div>",unsafe_allow_html=True)


def render_hod_overview(user):
    page_header("Department workspace", "See deterioration before it becomes a report.", "The department view aggregates runway, risk, and intervention signals so the HOD can decide where to follow up.")
    students = query_all("SELECT student_id,name FROM students WHERE department=?", (user["department"],))
    all_stats=[]
    for strow in students:
        for s in get_student_dashboard(strow["student_id"]):
            all_stats.append({**s, "student": strow["name"], "student_id": strow["student_id"]})
    if not all_stats:
        st.info("No department data yet.")
        return
    cols=st.columns(4)
    with cols[0]: metric("Students",len(students),"Department roster")
    with cols[1]: metric("At Risk",sum(x["risk_state"]=="At Risk" for x in all_stats),"Subjects")
    with cols[2]: metric("Critical",sum(x["risk_state"]=="Critical" for x in all_stats),"Subjects")
    with cols[3]: metric("Projected < threshold",sum(x["projected_pct"] < x["threshold"] for x in all_stats),"Subjects")
    st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
    c1,c2=st.columns([1.1,1])
    with c1:
        chart=pd.DataFrame({"State":["Safe","Watch","At Risk","Critical"],"Subjects":[sum(x["risk_state"]==s for x in all_stats) for s in ["Safe","Watch","At Risk","Critical"]]})
        st.markdown('<div class="card"><div class="card-title">Department risk distribution</div><div class="card-sub">Decision signal: how much of the roster needs attention?</div>',unsafe_allow_html=True)
        fig=px.bar(chart,x="State",y="Subjects",text="Subjects")
        fig.update_layout(height=320,margin=dict(l=10,r=10,t=20,b=10),paper_bgcolor="white",plot_bgcolor="white",font=dict(color="#344054"),showlegend=False)
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        st.markdown("</div>",unsafe_allow_html=True)
    with c2:
        subj=pd.DataFrame(all_stats)
        trend=subj.groupby("subject_code",as_index=False)["trend_pp"].mean().sort_values("trend_pp")
        st.markdown('<div class="card"><div class="card-title">Subjects with weakening trend</div><div class="card-sub">Recent attendance movement in percentage points.</div>',unsafe_allow_html=True)
        st.dataframe(trend.rename(columns={"subject_code":"Subject","trend_pp":"Avg trend (pp)"}),use_container_width=True,hide_index=True)
        st.markdown("</div>",unsafe_allow_html=True)


def render_admin_overview(user):
    counts = {
        "Students": query_one("SELECT COUNT(*) c FROM students")["c"],
        "Users": query_one("SELECT COUNT(*) c FROM users")["c"],
        "Sessions": query_one("SELECT COUNT(*) c FROM class_sessions")["c"],
        "Attendance records": query_one("SELECT COUNT(*) c FROM attendance_records")["c"],
    }
    page_header("Institution workspace", "Attendance intelligence control plane.", "Institution-wide visibility across data health, risk, policy, auditability, and operational workflow.")
    cols=st.columns(4)
    for col,(k,v) in zip(cols,counts.items()):
        with col: metric(k,v,"Live from SQLite")
    st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
    a,b=st.columns([1.2,1])
    with a:
        rows=query_all(
            """SELECT st.department,
                      COUNT(DISTINCT st.student_id) Students,
                      ROUND(AVG(CASE WHEN ar.status='Present' THEN 1.0 ELSE 0.0 END)*100,1) SessionAttendancePct
               FROM students st
               LEFT JOIN attendance_records ar ON ar.student_id=st.student_id
               GROUP BY st.department ORDER BY st.department"""
        )
        st.markdown('<div class="card"><div class="card-title">Department health</div><div class="card-sub">Observed attendance from stored records.</div>',unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        st.markdown("</div>",unsafe_allow_html=True)
    with b:
        attempts=query_all("SELECT status,COUNT(*) count FROM attendance_attempts GROUP BY status")
        st.markdown('<div class="card"><div class="card-title">Verification activity</div><div class="card-sub">Accepted vs rejected check-in attempts.</div>',unsafe_allow_html=True)
        if attempts:
            st.dataframe(pd.DataFrame(attempts),use_container_width=True,hide_index=True)
        st.markdown("</div>",unsafe_allow_html=True)


def page_overview(user):
    if user["role"]=="student": render_student_overview(user)
    elif user["role"]=="faculty": render_faculty_overview(user)
    elif user["role"]=="hod": render_hod_overview(user)
    else: render_admin_overview(user)


# ---------------------------
# Login
# ---------------------------
user=current_user()
if not user:
    st.markdown('<div class="login-wrap"><div class="login-card">',unsafe_allow_html=True)
    st.markdown(
        f'<div class="brand"><div class="brand-mark">✓</div><div><div class="brand-title">{PRODUCT_NAME}</div><div class="brand-sub">{PRODUCT_TAGLINE.upper()}</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("### Sign in")
    st.caption("Use a seeded demo account or your institution account.")
    with st.form("login"):
        username=st.text_input("Username",placeholder="e.g. faculty")
        password=st.text_input("Password",type="password",placeholder="Enter password")
        submit=st.form_submit_button("Sign in",type="primary",use_container_width=True)
    if submit:
        result = do_login(username,password)
        if result is True:
            st.rerun()
        elif result == "locked":
            st.error("Too many failed attempts. Try again after the 10-minute lock window.")
        else:
            st.error("Invalid credentials or inactive account.")
    st.markdown(
        '<div class="notice"><strong>Demo credentials</strong><br>'
        'Admin: <code>admin / admin123</code><br>'
        'HOD: <code>hod / hod123</code><br>'
        'Faculty: <code>faculty / faculty123</code><br>'
        'Student: <code>student1 / student123</code></div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div></div>",unsafe_allow_html=True)
    st.stop()

# ---------------------------
# Shell
# ---------------------------
nav=role_nav(user["role"])
if st.session_state.page not in nav:
    st.session_state.page=nav[0]

with st.sidebar:
    st.markdown(
        f'<div class="brand"><div class="brand-mark">✓</div><div><div class="brand-title">{PRODUCT_NAME}</div><div class="brand-sub">{PRODUCT_TAGLINE.upper()}</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="nav-head">Workspace</div>',unsafe_allow_html=True)
    choice=st.radio("Navigation",nav,index=nav.index(st.session_state.page),label_visibility="collapsed")
    if choice != st.session_state.page:
        st.session_state.page=choice
        st.rerun()
    st.markdown("---")
    unread=len(list_notifications(user["id"], unread_only=True))
    st.markdown(
        f'<div class="sidebar-footer"><div style="font-weight:700;font-size:12px;">{escape(user["full_name"])}</div>'
        f'<div style="font-size:10px;color:#98a2b3;margin-top:2px;">{escape(user["role"].upper())}'
        f'{" · "+escape(user["department"]) if user["department"] else ""}</div>'
        f'<div style="font-size:10px;color:#667085;margin-top:8px;">{unread} unread notification{"s" if unread!=1 else ""}</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Sign out",use_container_width=True):
        logout()

from zoneinfo import ZoneInfo
now=datetime.now(ZoneInfo(TIMEZONE_NAME))
st.markdown(
    f'<div class="topbar"><div><small>{now.strftime("%A, %d %B %Y")}</small><br><strong>{PRODUCT_NAME} · {PRODUCT_TAGLINE}</strong></div>'
    f'<div class="profile"><div class="avatar">{escape(user["full_name"][:1].upper())}</div><div><div style="font-weight:700;font-size:11px;">{escape(user["full_name"])}</div>'
    f'<div style="font-size:9px;color:#98a2b3;">{escape(user["role"].title())}</div></div></div></div>',
    unsafe_allow_html=True,
)

# ---------------------------
# Student pages
# ---------------------------
if user["role"]=="student" and st.session_state.page=="Overview":
    page_overview(user)

elif user["role"]=="student" and st.session_state.page=="My Attendance":
    stats=get_student_dashboard(user["student_id"])
    refresh_student_notifications(user["student_id"],stats)
    page_header("Student intelligence","My attendance","Subject-by-subject runway, projected outcome, and explainable risk.")
    for s in stats:
        runway_card(s)
        with st.expander(f"{s['subject_code']} · Why this state?"):
            st.write(explain_risk({"state":s["risk_state"],"signals":s["risk_signals"]},s))
            if s["risk_signals"]:
                for signal in s["risk_signals"]:
                    st.markdown(f'<div class="signal">• {escape(signal)}</div>',unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)
    subjects=query_all("SELECT id,code,name FROM subjects JOIN enrollments e ON e.subject_id=subjects.id WHERE e.student_id=? ORDER BY code",(user["student_id"],))
    subject_map={s["code"]:s for s in subjects}
    chosen=st.selectbox("Attendance history subject",["All subjects"]+list(subject_map.keys()))
    subject_id=subject_map[chosen]["id"] if chosen!="All subjects" else None
    hist=attendance_history(user["student_id"],subject_id)
    if not hist.empty:
        hist["Date"]=pd.to_datetime(hist["Date"])
        st.dataframe(hist,use_container_width=True,hide_index=True)
        fig=px.line(hist.sort_values("Date"),x="Date",y=hist["Status"].eq("Present").astype(int),markers=True)
        fig.update_yaxes(tickmode="array",tickvals=[0,1],ticktext=["Absent","Present"])
        fig.update_layout(height=260,margin=dict(l=10,r=10,t=20,b=10),paper_bgcolor="white",plot_bgcolor="white",font=dict(color="#344054"))
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    else:
        st.info("No attendance history has been recorded yet.")

elif user["role"]=="student" and st.session_state.page=="Verify Attendance":
    page_header("Verified capture","Verify attendance","Use the current rotating QR token shown by faculty. The token expires quickly and each student/session can be recorded only once.")
    st.markdown('<div class="notice"><strong>Trust flow:</strong> signed rotating token → student enrollment check → duplicate check → registered device identity → auditable attendance event.</div>',unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)
    c1,c2=st.columns([1.2,1])
    with c1:
        token=st.text_input("Attendance token",placeholder="Paste or scan the current AX1 token")
        st.caption(f"Current browser device identity: {st.session_state.device_id[:8]}…")
        label=st.text_input("Device label",value="My primary device")
        if st.button("Register this device",use_container_width=True):
            from services.attendance_service import device_hash
            from db import execute
            execute(
                """INSERT INTO device_registrations(student_id,device_hash,label,created_at,last_seen)
                   VALUES (?,?,?,?,?) ON CONFLICT(student_id,device_hash) DO UPDATE SET label=excluded.label,last_seen=excluded.last_seen""",
                (user["student_id"],device_hash(st.session_state.device_id),label,utc_now_iso(),utc_now_iso()),
            )
            audit(user["id"],"register_device","device_registration",user["student_id"],{"label":label})
            st.success("Device registered for this student account.")
        if st.button("Submit verified attendance",type="primary",use_container_width=True):
            try:
                from services.attendance_service import device_hash
                registered = query_one(
                    "SELECT 1 FROM device_registrations WHERE student_id=? AND device_hash=? AND active=1",
                    (user["student_id"],device_hash(st.session_state.device_id)),
                )
                if not registered:
                    raise ValueError("This browser device is not registered. Register it first, then submit the current QR.")
                submit_qr_attendance(token.strip(),user["student_id"],st.session_state.device_id)
                st.success("Attendance verified and recorded.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    with c2:
        st.markdown('<div class="card"><div class="card-title">Privacy by design</div><div class="card-sub">What is stored for verification</div><div style="height:8px"></div>'
                    '• A salted device hash, not a raw device identifier<br>'
                    '• Session + attendance event<br>'
                    '• Verification outcome and reason<br>'
                    '• Audit history for operational review<br><br>'
                    'No continuous GPS or facial recognition is required.</div>',unsafe_allow_html=True)

elif user["role"]=="student" and st.session_state.page=="Requests":
    page_header("Student requests","Corrections & condonation","Submit traceable requests when the recorded state needs human review.")
    stats=get_student_dashboard(user["student_id"])
    subjects=query_all("SELECT s.* FROM subjects s JOIN enrollments e ON e.subject_id=s.id WHERE e.student_id=? ORDER BY s.code",(user["student_id"],))
    subject_map={s["code"]:s for s in subjects}
    t1,t2=st.tabs(["Correction request","Condonation request"])
    with t1:
        sessions=query_all(
            """SELECT cs.id,cs.session_date,s.code subject_code,s.name subject_name
               FROM class_sessions cs JOIN subjects s ON s.id=cs.subject_id
               JOIN enrollments e ON e.subject_id=s.id AND e.student_id=?
               ORDER BY cs.session_date DESC LIMIT 30""",(user["student_id"],)
        )
        sess_map={f"{x['session_date']} · {x['subject_code']}":x for x in sessions}
        if sess_map:
            selected=st.selectbox("Session",list(sess_map))
            desired=st.selectbox("Requested status",["Present","Excused"])
            reason=st.text_area("Reason",placeholder="Explain what needs correction.")
            doc=st.file_uploader("Supporting document (optional)",type=["pdf","png","jpg"],key="corrdoc")
            if st.button("Submit correction request",type="primary"):
                if not reason.strip():
                    st.error("Please provide a reason.")
                else:
                    doc_name=None
                    if doc:
                        doc_name=f"{user['student_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{doc.name}"
                        (DATA_DIR/"documents"/doc_name).write_bytes(doc.getbuffer())
                    submit_correction_request(sess_map[selected]["id"],user["student_id"],desired,reason.strip(),doc_name,user["id"])
                    audit(user["id"],"submit_correction","correction_request",sess_map[selected]["id"],{"student_id":user["student_id"]})
                    st.success("Request submitted for human review.")
        else:
            st.info("No eligible sessions found.")
    with t2:
        chosen=st.selectbox("Subject",list(subject_map.keys()),key="cond_subject")
        reason=st.text_area("Why are you requesting condonation?",key="cond_reason",placeholder="Provide the documented reason.")
        doc=st.file_uploader("Supporting document",type=["pdf","png","jpg"],key="conddoc")
        if st.button("Submit condonation request",type="primary"):
            if not reason.strip():
                st.error("Please provide a reason.")
            else:
                doc_name=None
                if doc:
                    doc_name=f"{user['student_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{doc.name}"
                    (DATA_DIR/"documents"/doc_name).write_bytes(doc.getbuffer())
                submit_condonation_request(user["student_id"],subject_map[chosen]["id"],reason.strip(),doc_name,user["id"])
                audit(user["id"],"submit_condonation","condonation_request",user["student_id"],{"subject_id":subject_map[chosen]["id"]})
                st.success("Condonation request submitted.")
    st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)
    own_corr=query_all("SELECT * FROM correction_requests WHERE requested_by=? ORDER BY created_at DESC LIMIT 15",(user["id"],))
    own_cond=query_all("SELECT * FROM condonation_requests WHERE requested_by=? ORDER BY created_at DESC LIMIT 15",(user["id"],))
    st.dataframe(pd.DataFrame(own_corr),use_container_width=True,hide_index=True)
    st.dataframe(pd.DataFrame(own_cond),use_container_width=True,hide_index=True)

elif user["role"]=="student" and st.session_state.page=="Notifications":
    page_header("Attention queue","Notifications","Critical items are surfaced first and non-critical information is batched.")
    notes=list_notifications(user["id"])
    if not notes:
        st.success("No notifications right now.")
    for n in notes:
        cls={"Critical":"critical","High":"risk","Medium":"watch","Informational":"safe"}.get(n["priority"],"watch")
        st.markdown(
            f'<div class="card" style="margin-bottom:8px"><div style="display:flex;justify-content:space-between">'
            f'<strong>{escape(n["title"])}</strong><span class="status {cls}">{escape(n["priority"])}</span></div>'
            f'<div class="table-note">{escape(n["message"])}</div><div style="margin-top:8px">'
            f'{"Read" if n["read_at"] else ""}</div></div>',unsafe_allow_html=True)
        if not n["read_at"]:
            if st.button("Mark read",key=f"read_{n['id']}"):
                mark_read(n["id"],user["id"]); st.rerun()

# ---------------------------
# Staff pages: faculty
# ---------------------------
elif user["role"]=="faculty" and st.session_state.page=="Overview":
    page_overview(user)

elif user["role"]=="faculty" and st.session_state.page=="Take Attendance":
    page_header("Capture","Take attendance","Open a session, rotate a short-lived verification token, or use the faculty fallback when needed.")
    subjects=query_all("SELECT * FROM subjects WHERE department=? ORDER BY code",(user["department"] or "CSE",))
    if not subjects:
        st.warning("No subjects are configured for this faculty department.")
    else:
        smap={f"{s['code']} · {s['name']}":s for s in subjects}
        selected=st.selectbox("Subject",list(smap))
        start=st.text_input("Start time",value="10:00")
        end=st.text_input("End time",value="11:00")
        if st.button("Open new attendance session",type="primary"):
            from services.attendance_service import create_session
            sid=create_session(smap[selected]["id"],user["id"],start,end)
            st.session_state.active_session_id=sid
            st.session_state.active_token=None
            st.session_state.active_token_expires=None
            st.success(f"Session #{sid} opened.")
            st.rerun()
        open_sessions=query_all(
            """SELECT cs.id,cs.session_date,cs.start_time,cs.end_time,cs.status,s.code,s.name
               FROM class_sessions cs JOIN subjects s ON s.id=cs.subject_id
               WHERE cs.created_by=? AND cs.status='open'
               ORDER BY cs.created_at DESC""",(user["id"],)
        )
        if open_sessions:
            labels={f"#{x['id']} · {x['code']} · {x['session_date']}":x for x in open_sessions}
            active_label=st.selectbox("Open session",list(labels),index=0)
            active=labels[active_label]
            tok,exp=ensure_token(active["id"])
            a,b=st.columns([1,1.1])
            with a:
                st.image(qr_png(tok),width=280)
                st.caption(f"Token rotates automatically after expiry. Expires {exp.astimezone().strftime('%H:%M:%S')}.")
                st.code(tok,language="text")
                if st.button("Rotate verification code",use_container_width=True):
                    st.session_state.active_token=None
                    st.session_state.active_token_expires=None
                    st.rerun()
                if st.button("Close session",type="primary",use_container_width=True):
                    from db import execute
                    execute("UPDATE class_sessions SET status='closed' WHERE id=?",(active["id"],))
                    audit(user["id"],"close_attendance_session","class_session",active["id"])
                    st.session_state.active_session_id=None
                    st.success("Session closed.")
                    st.rerun()
            with b:
                summary=session_summary(active["id"])
                roster=summary["roster"]
                df=pd.DataFrame(roster)
                if not df.empty:
                    present=int((df["status"]=="Present").sum())
                    metric("Live attendance",f"{present}/{len(df)}",f"{present/len(df)*100:.1f}% captured")
                    search=st.text_input("Find student",placeholder="Name or ID",key="faculty_search")
                    if search.strip():
                        q=search.strip().lower()
                        df=df[df["name"].str.lower().str.contains(q)|df["student_id"].astype(str).str.lower().str.contains(q)]
                    st.dataframe(df[["student_id","name","status","source"]],use_container_width=True,hide_index=True)
                    selected_ids=st.multiselect("Faculty fallback: mark selected students present",df["student_id"].tolist())
                    if st.button("Mark selected present",use_container_width=True):
                        for sid in selected_ids:
                            mark_faculty_attendance(active["id"],str(sid),"Present",user["id"])
                        st.success("Selected students marked present.")
                        st.rerun()
                    queue_payload=[{"client_event_id":f"offline-{active['id']}-{row['student_id']}","session_id":active["id"],"student_id":row["student_id"],"status":row["status"]} for row in roster]
                    st.download_button("Export local sync queue",json.dumps(queue_payload,indent=2),file_name=f"attendx_session_{active['id']}_queue.json",mime="application/json")

elif user["role"]=="faculty" and st.session_state.page=="Risk Monitor":
    page_header("Risk operations","Student risk monitor","Prioritize students by explainable risk signals, runway, and intervention need.")
    students=query_all("SELECT student_id,name,department FROM students WHERE department=?",(user["department"] or "CSE",))
    rows=[]
    for strow in students:
        for s in get_student_dashboard(strow["student_id"]):
            if s["risk_state"] in ("Critical","At Risk","Watch"):
                rows.append({**s,"Student":strow["name"],"Student ID":strow["student_id"]})
    if rows:
        df=pd.DataFrame(rows).sort_values(["risk_state","current_pct"],key=lambda col: col.map({"Critical":0,"At Risk":1,"Watch":2}).fillna(3) if col.name=="risk_state" else col)
        st.dataframe(df[["Student","Student ID","subject_code","current_pct","projected_pct","consecutive_absences","risk_state"]],use_container_width=True,hide_index=True)
        st.markdown("### Start an intervention")
        for row in rows[:12]:
            with st.expander(f"{row['Student']} · {row['subject_code']} · {row['risk_state']}"):
                st.write(explain_risk({"state":row["risk_state"],"signals":row["risk_signals"]},row))
                action=f"Attend the next {row['needed_next_window']} of the next {row['next_window']} planned sessions."
                st.caption(action)
                if st.button("Create intervention task",key=f"int_{row['student_id']}_{row['subject_id']}"):
                    create_intervention(row["student_id"],row["subject_id"],"Attendance risk",action,owner_role="faculty",due_days=7)
                    audit(user["id"],"create_intervention","intervention",row["student_id"],{"subject_id":row["subject_id"]})
                    st.success("Intervention created and added to the department queue.")
    else:
        st.success("No Watch, At Risk, or Critical subjects detected.")

elif user["role"]=="faculty" and st.session_state.page=="Session Review":
    page_header("Trust operations","Session review","Review evidence before acting on suspicious attendance. Algorithms flag; humans decide.")
    sessions=query_all(
        """SELECT cs.id,cs.session_date,cs.start_time,cs.end_time,cs.status,s.code,s.name
           FROM class_sessions cs JOIN subjects s ON s.id=cs.subject_id
           WHERE cs.created_by=? ORDER BY cs.session_date DESC LIMIT 40""",(user["id"],)
    )
    if sessions:
        smap={f"#{s['id']} · {s['session_date']} · {s['code']}":s for s in sessions}
        chosen=st.selectbox("Session",list(smap))
        sess=smap[chosen]
        findings=detect_session_anomalies(sess["id"])
        label=session_trust_label(findings)
        st.markdown(f'<div class="notice"><strong>Session trust state:</strong> {escape(label)}. Findings are evidence for human review, not automatic punishment.</div>',unsafe_allow_html=True)
        if findings:
            st.dataframe(pd.DataFrame(findings),use_container_width=True,hide_index=True)
        else:
            st.success("No material session-level anomaly was detected.")
        attempts=query_all("SELECT attempted_at,student_id,status,reason FROM attendance_attempts WHERE session_id=? ORDER BY attempted_at DESC",(sess["id"],))
        if attempts:
            st.markdown("#### Verification trail")
            st.dataframe(pd.DataFrame(attempts),use_container_width=True,hide_index=True)
    else:
        st.info("No sessions available.")

elif user["role"]=="faculty" and st.session_state.page=="Corrections":
    page_header("Human review","Correction queue","Approve or reject attendance changes with reasons. Every decision is written to the audit log.")
    t1,t2=st.tabs(["Corrections","Condonation"])
    with t1:
        reqs=list_correction_requests(user["department"])
        if not reqs:
            st.success("No pending correction requests.")
        for r in reqs:
            with st.expander(f"#{r['id']} · {r['name']} · {r['subject_code']} · {r['session_date']}"):
                st.write(r["reason"])
                if r["document_name"]:
                    st.caption(f"Document: {r['document_name']}")
                note=st.text_input("Review note",key=f"crnote{r['id']}")
                a,b=st.columns(2)
                if a.button("Approve",key=f"crap{r['id']}",type="primary"):
                    review_correction(r["id"],user["id"],"Approved",note); st.success("Approved."); st.rerun()
                if b.button("Reject",key=f"crrej{r['id']}"):
                    review_correction(r["id"],user["id"],"Rejected",note); st.success("Rejected."); st.rerun()
    with t2:
        reqs=list_condonation_requests(user["department"])
        if not reqs:
            st.success("No pending condonation requests.")
        for r in reqs:
            with st.expander(f"#{r['id']} · {r['name']} · {r['subject_code']}"):
                st.write(r["reason"])
                if r["document_name"]: st.caption(f"Document: {r['document_name']}")
                note=st.text_input("Review note",key=f"canote{r['id']}")
                a,b=st.columns(2)
                if a.button("Approve",key=f"coap{r['id']}",type="primary"):
                    review_condonation(r["id"],user["id"],"Approved",note); st.success("Approved."); st.rerun()
                if b.button("Reject",key=f"corej{r['id']}"):
                    review_condonation(r["id"],user["id"],"Rejected",note); st.success("Rejected."); st.rerun()

elif user["role"]=="faculty" and st.session_state.page=="Sync Center":
    page_header("Recovery workflow","Offline sync center","Reconcile a queue captured during a temporary connectivity failure. Events are idempotent and validated before applying.")
    st.markdown(
        '<div class="notice"><strong>Offline-first contract:</strong> capture events into a local JSON queue, then upload that queue here when connectivity returns. AttendX never reports an event as synchronized until the server accepts it.</div>',
        unsafe_allow_html=True,
    )
    uploaded=st.file_uploader("Offline queue JSON",type=["json"],key="sync_upload")
    if uploaded:
        try:
            payload=json.loads(uploaded.getvalue().decode("utf-8"))
            st.caption(f"{len(payload) if isinstance(payload,list) else 0} event(s) detected")
            if isinstance(payload,list):
                st.dataframe(pd.DataFrame(payload),use_container_width=True,hide_index=True)
            if st.button("Validate & apply queue",type="primary"):
                from services.sync import apply_queue
                result=apply_queue(payload,user["id"])
                st.success(f"Applied {result['applied']} event(s); rejected {result['rejected']}.")
                st.dataframe(pd.DataFrame(result["results"]),use_container_width=True,hide_index=True)
        except Exception as exc:
            st.error(f"Could not apply queue: {exc}")
    recent=query_all("SELECT id,client_event_id,status,created_at,applied_at,reason FROM sync_events ORDER BY created_at DESC LIMIT 30")
    if recent:
        st.markdown("#### Recent sync events")
        st.dataframe(pd.DataFrame(recent),use_container_width=True,hide_index=True)

elif user["role"]=="faculty" and st.session_state.page=="Reports":
    page_header("Operational reporting","Reports","Export actual attendance data instead of generated or simulated figures.")
    report=faculty_session_report(user["id"],days=180)
    if report.empty:
        st.info("No faculty-owned sessions found.")
    else:
        st.dataframe(report,use_container_width=True,hide_index=True)
        st.download_button("Download CSV",report.to_csv(index=False),file_name="attendx_faculty_report.csv",mime="text/csv")
        fig=px.line(report.sort_values("Date"),x="Date",y="AttendancePct",color="Subject",markers=True)
        fig.update_layout(height=330,margin=dict(l=10,r=10,t=20,b=10),paper_bgcolor="white",plot_bgcolor="white",font=dict(color="#344054"))
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

# ---------------------------
# HOD pages
# ---------------------------
elif user["role"]=="hod" and st.session_state.page=="Overview":
    page_overview(user)

elif user["role"]=="hod" and st.session_state.page=="Department Intelligence":
    render_hod_overview(user)

elif user["role"]=="hod" and st.session_state.page=="Interventions":
    page_header("Intervention operations","Intervention tracker","Track whether early warnings turn into actions and outcomes.")
    ints=list_interventions(user["department"],open_only=False)
    if ints:
        st.dataframe(pd.DataFrame(ints)[["id","name","student_id","subject_code","trigger_type","recommendation","status","due_date","created_at","resolved_at"]],use_container_width=True,hide_index=True)
        for i in ints[:15]:
            with st.expander(f"#{i['id']} · {i['name']} · {i.get('subject_code') or 'General'} · {i['status']}"):
                status=st.selectbox("Status",["Open","In Progress","Resolved"],index=["Open","In Progress","Resolved"].index(i["status"]),key=f"istatus{i['id']}")
                note=st.text_area("Notes",value=i.get("notes") or "",key=f"inote{i['id']}")
                if st.button("Save",key=f"isave{i['id']}"):
                    update_intervention(i["id"],status,note)
                    st.success("Updated.")
                    st.rerun()
    else:
        st.info("No interventions yet.")

elif user["role"]=="hod" and st.session_state.page=="Reports":
    page_header("Department reporting","Reports","Evidence-based reporting for the department.")
    rows=[]
    for strow in query_all("SELECT student_id,name FROM students WHERE department=?",(user["department"],)):
        for s in get_student_dashboard(strow["student_id"]):
            rows.append({"Student":strow["name"],"ID":strow["student_id"],"Subject":s["subject_code"],"Attendance %":s["current_pct"],"Projected %":s["projected_pct"],"Risk":s["risk_state"]})
    df=pd.DataFrame(rows)
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.download_button("Download department risk report",df.to_csv(index=False),file_name="attendx_department_risk.csv",mime="text/csv")

# ---------------------------
# Admin pages
# ---------------------------
elif user["role"]=="admin" and st.session_state.page=="Overview":
    page_overview(user)

elif user["role"]=="admin" and st.session_state.page=="Departments":
    page_header("Institution structure","Departments","Review risk by department and identify where the operational picture is changing.")
    departments=query_all("SELECT DISTINCT department FROM students ORDER BY department")
    rows=[]
    for d in departments:
        dept=d["department"]
        stats=[]
        for strow in query_all("SELECT student_id FROM students WHERE department=?",(dept,)):
            stats.extend(get_student_dashboard(strow["student_id"]))
        rows.append({
            "Department":dept,
            "Students":query_one("SELECT COUNT(*) c FROM students WHERE department=?",(dept,))["c"],
            "Critical":sum(s["risk_state"]=="Critical" for s in stats),
            "At Risk":sum(s["risk_state"]=="At Risk" for s in stats),
            "Watch":sum(s["risk_state"]=="Watch" for s in stats),
            "Safe":sum(s["risk_state"]=="Safe" for s in stats),
            "Projected below threshold":sum(s["projected_pct"]<s["threshold"] for s in stats),
        })
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

elif user["role"]=="admin" and st.session_state.page=="Roster":
    page_header("Institution structure","Student roster","Import and maintain the roster without wiping historical attendance.")
    st.markdown(
        '<div class="notice"><strong>Import contract:</strong> CSV must contain student_id, name, department, year. Existing student IDs are updated; historical attendance is not deleted.</div>',
        unsafe_allow_html=True,
    )
    uploaded=st.file_uploader("Student CSV",type=["csv"],key="roster_csv")
    if uploaded:
        try:
            df=pd.read_csv(uploaded)
            required={"student_id","name","department","year"}
            missing=required-set(df.columns)
            if missing:
                st.error("Missing required column(s): "+", ".join(sorted(missing)))
            else:
                st.dataframe(df.head(25),use_container_width=True,hide_index=True)
                if st.button("Validate & import roster",type="primary"):
                    clean=df.copy()
                    clean["student_id"]=clean["student_id"].astype(str).str.strip()
                    clean["name"]=clean["name"].astype(str).str.strip()
                    clean["department"]=clean["department"].astype(str).str.strip().str.upper()
                    clean["year"]=pd.to_numeric(clean["year"],errors="coerce")
                    invalid=clean[clean["student_id"].eq("")|clean["name"].eq("")|clean["year"].isna()]
                    dupes=clean[clean["student_id"].duplicated(keep=False)]
                    if not invalid.empty:
                        st.error("Validation failed: blank identity fields or invalid year values were detected.")
                    elif not dupes.empty:
                        st.error("Validation failed: duplicate student IDs are present.")
                    else:
                        from db import execute
                        for row in clean.to_dict("records"):
                            execute(
                                """INSERT INTO students(student_id,name,department,year,created_at)
                                   VALUES (?,?,?,?,?)
                                   ON CONFLICT(student_id) DO UPDATE SET
                                     name=excluded.name,department=excluded.department,year=excluded.year""",
                                (str(row["student_id"]),row["name"],row["department"],int(row["year"]),utc_now_iso()),
                            )
                        audit(user["id"],"import_roster","student",None,{"rows":len(clean)})
                        st.success(f"Imported/updated {len(clean)} roster records.")
                        st.rerun()
        except Exception as exc:
            st.error(f"Could not process roster: {exc}")
    roster=query_all("SELECT student_id,name,department,year,created_at FROM students ORDER BY department,student_id")
    st.dataframe(pd.DataFrame(roster),use_container_width=True,hide_index=True)
    st.download_button("Export current roster",pd.DataFrame(roster).to_csv(index=False),file_name="attendx_roster.csv",mime="text/csv")

elif user["role"]=="admin" and st.session_state.page=="Users":
    page_header("Access control","Users","Role-based access for students, faculty, HODs, and administrators.")
    existing=query_all("SELECT username,full_name,role,student_id,department,active,created_at FROM users ORDER BY role,username")
    st.dataframe(pd.DataFrame(existing),use_container_width=True,hide_index=True)
    with st.expander("Create user"):
        with st.form("new_user"):
            username=st.text_input("Username")
            full_name=st.text_input("Full name")
            role=st.selectbox("Role",["student","faculty","hod","admin"])
            password=st.text_input("Temporary password",type="password")
            student_id=st.text_input("Student ID (students only)")
            department=st.text_input("Department")
            submitted=st.form_submit_button("Create user",type="primary")
        if submitted:
            if not username or not full_name or len(password)<10:
                st.error("Username, full name, and a password of at least 10 characters are required.")
            else:
                try:
                    from db import execute
                    execute(
                        """INSERT INTO users(username,full_name,role,password_hash,student_id,department,created_at)
                           VALUES (?,?,?,?,?,?,?)""",
                        (username.strip(),full_name.strip(),role,hash_password(password),student_id.strip() or None,department.strip() or None,utc_now_iso())
                    )
                    audit(user["id"],"create_user","user",username,{"role":role})
                    st.success("User created.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not create user: {exc}")

elif user["role"]=="admin" and st.session_state.page=="Audit Log":
    page_header("Governance","Audit log","Who changed what, when, and why.")
    logs=query_all(
        """SELECT a.created_at,a.action,a.entity_type,a.entity_id,u.username,a.details_json
           FROM audit_logs a LEFT JOIN users u ON u.id=a.actor_user_id
           ORDER BY a.created_at DESC LIMIT 250"""
    )
    st.dataframe(pd.DataFrame(logs),use_container_width=True,hide_index=True)

elif user["role"]=="admin" and st.session_state.page=="System Health":
    page_header("Operations","System health","Runtime checks for the local production-like deployment.")
    import sqlite3
    checks=[
        ("Database file",str(DB_PATH),DB_PATH.exists()),
        ("Database readable", "SQLite connection", query_one("SELECT 1 c")["c"]==1),
        ("Documents folder",str(DATA_DIR/"documents"),(DATA_DIR/"documents").exists()),
        ("Secret configured", "ATTENDX_SECRET_KEY", bool(os.getenv("ATTENDX_SECRET_KEY"))),
        ("Audit entries", str(query_one("SELECT COUNT(*) c FROM audit_logs")["c"]), True),
        ("Rejected verification attempts", str(query_one("SELECT COUNT(*) c FROM attendance_attempts WHERE status='Rejected'")["c"]), True),
    ]
    st.dataframe(pd.DataFrame(checks,columns=["Check","Value","OK"]),use_container_width=True,hide_index=True)
    st.caption("The development fallback secret is intentionally flagged. Set ATTENDX_SECRET_KEY before production deployment.")

elif user["role"]=="admin" and st.session_state.page=="Policy":
    page_header("Governance","Attendance policy","Configure the policy threshold used by runway and risk calculations.")
    current=float(get_setting("attendance_threshold","75"))
    with st.form("policy"):
        threshold=st.slider("Minimum attendance threshold (%)",min_value=50.0,max_value=95.0,value=current,step=0.5)
        semester=get_setting("semester_label","2026–27 Semester")
        semester_end=get_setting("semester_end","2027-04-30")
        label=st.text_input("Semester label",semester)
        end=st.text_input("Semester end (YYYY-MM-DD)",semester_end)
        save=st.form_submit_button("Save policy",type="primary")
    if save:
        try:
            date.fromisoformat(end)
            set_setting("attendance_threshold",threshold,user["id"])
            set_setting("semester_label",label,user["id"])
            set_setting("semester_end",end,user["id"])
            st.success("Policy updated.")
            st.rerun()
        except ValueError:
            st.error("Semester end must use YYYY-MM-DD.")

# ---------------------------
# Global staff sync center notice
# ---------------------------
st.markdown(
    f'<div class="footer">{PRODUCT_NAME} · {PRODUCT_TAGLINE} · Durable SQLite storage · Deterministic runway/risk engine · Human-reviewed anomalies · {get_setting("semester_label","Current semester")}</div>',
    unsafe_allow_html=True,
)
