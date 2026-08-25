import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import save_attendance

# ============================================================
# ATTENDX — PRODUCT UI V1
# Modern SaaS-style Streamlit interface
# Existing attendance functionality is preserved.
# ============================================================

st.set_page_config(
    page_title="AttendX | Smart Attendance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# DESIGN SYSTEM
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #07111f;
    --panel: #0d1a2b;
    --panel-2: #101f33;
    --border: rgba(148,163,184,.13);
    --text: #f8fafc;
    --muted: #8fa1b8;
    --primary: #3b82f6;
    --primary-2: #60a5fa;
    --success: #22c55e;
    --danger: #ef4444;
    --warning: #f59e0b;
}

* {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 15% 0%, rgba(59,130,246,.12), transparent 28%),
        radial-gradient(circle at 90% 10%, rgba(14,165,233,.08), transparent 25%),
        var(--bg);
    color: var(--text);
}

.main .block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
}

/* Hide Streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
    background: transparent;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #091524 0%, #07111f 100%);
    border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.2rem;
}

.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 10px 20px 10px;
}

.brand-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #2563eb, #38bdf8);
    box-shadow: 0 8px 25px rgba(37,99,235,.30);
    font-size: 22px;
}

.brand-name {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -.5px;
}

.brand-subtitle {
    color: #71839b;
    font-size: 11px;
    margin-top: 2px;
}

.nav-label {
    color: #64748b;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
    margin: 18px 10px 8px;
}

/* Radio navigation */
div[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 5px;
}

div[data-testid="stSidebar"] div[role="radiogroup"] label {
    border-radius: 10px;
    padding: 9px 10px;
    border: 1px solid transparent;
    transition: all .2s ease;
}

div[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(59,130,246,.08);
    border-color: rgba(59,130,246,.15);
}

div[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
    background: linear-gradient(90deg, rgba(59,130,246,.18), rgba(59,130,246,.06));
    border-color: rgba(59,130,246,.25);
}

.sidebar-bottom {
    margin-top: 28px;
    padding: 15px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: rgba(255,255,255,.025);
}

.sidebar-status {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #cbd5e1;
    font-size: 12px;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 10px rgba(34,197,94,.7);
}

/* Top bar */
.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 28px;
    padding: 14px 18px;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: rgba(13,26,43,.72);
    backdrop-filter: blur(18px);
}

.topbar-left small {
    color: var(--muted);
    font-size: 12px;
}

.topbar-left strong {
    display: block;
    margin-top: 2px;
    font-size: 15px;
}

.profile-chip {
    display: flex;
    align-items: center;
    gap: 9px;
    color: #cbd5e1;
    font-size: 12px;
}

.avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: white;
    font-weight: 800;
}

/* Page headers */
.page-kicker {
    color: #60a5fa;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.6px;
    margin-bottom: 7px;
}

.page-title {
    color: #f8fafc;
    font-size: 31px;
    line-height: 1.1;
    font-weight: 800;
    letter-spacing: -.8px;
    margin: 0;
}

.page-description {
    color: #8fa1b8;
    font-size: 13px;
    margin-top: 8px;
    margin-bottom: 24px;
}

/* Hero */
.hero {
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(96,165,250,.20);
    border-radius: 24px;
    padding: 44px;
    background:
        radial-gradient(circle at 85% 20%, rgba(56,189,248,.18), transparent 25%),
        radial-gradient(circle at 65% 90%, rgba(37,99,235,.16), transparent 30%),
        linear-gradient(135deg, #0d1d32, #091523);
    box-shadow: 0 25px 70px rgba(0,0,0,.24);
}

.hero-badge {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(59,130,246,.12);
    border: 1px solid rgba(96,165,250,.18);
    color: #93c5fd;
    font-size: 11px;
    font-weight: 700;
}

.hero h1 {
    font-size: 46px;
    line-height: 1;
    margin: 18px 0 12px;
    letter-spacing: -1.8px;
}

.hero p {
    max-width: 650px;
    color: #94a3b8;
    font-size: 15px;
    line-height: 1.7;
    margin-bottom: 24px;
}

.hero-grid {
    position: absolute;
    right: -80px;
    top: -90px;
    width: 360px;
    height: 360px;
    border-radius: 50%;
    border: 1px solid rgba(96,165,250,.08);
    box-shadow:
        0 0 0 40px rgba(96,165,250,.025),
        0 0 0 80px rgba(96,165,250,.02);
}

/* Cards */
.metric-card {
    min-height: 132px;
    padding: 20px;
    border: 1px solid var(--border);
    border-radius: 18px;
    background: linear-gradient(145deg, rgba(16,31,51,.92), rgba(10,22,37,.92));
    box-shadow: 0 12px 35px rgba(0,0,0,.16);
    transition: transform .2s ease, border-color .2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(96,165,250,.25);
}

.metric-label {
    color: #8497ad;
    font-size: 12px;
    font-weight: 600;
}

.metric-value {
    color: #f8fafc;
    font-size: 31px;
    font-weight: 800;
    margin-top: 9px;
}

.metric-note {
    color: #64748b;
    font-size: 11px;
    margin-top: 5px;
}

.metric-icon {
    float: right;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(59,130,246,.12);
    font-size: 17px;
}

/* Section cards */
.section-card {
    padding: 22px;
    border: 1px solid var(--border);
    border-radius: 18px;
    background: rgba(13,26,43,.72);
    margin-bottom: 18px;
}

.section-title {
    font-size: 16px;
    font-weight: 700;
    color: #f1f5f9;
}

.section-subtitle {
    color: #71839b;
    font-size: 12px;
    margin-top: 4px;
}

/* Feature cards */
.feature-card {
    height: 100%;
    padding: 23px;
    border: 1px solid var(--border);
    border-radius: 17px;
    background: linear-gradient(145deg, rgba(16,31,51,.82), rgba(10,22,37,.75));
    transition: all .2s ease;
}

.feature-card:hover {
    transform: translateY(-3px);
    border-color: rgba(59,130,246,.28);
}

.feature-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(59,130,246,.12);
    font-size: 20px;
    margin-bottom: 14px;
}

.feature-card h3 {
    font-size: 15px;
    margin: 0 0 7px;
}

.feature-card p {
    color: #8192a8;
    font-size: 12px;
    line-height: 1.6;
}

/* Student cards */
.student-card {
    padding: 18px;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: linear-gradient(145deg, rgba(16,31,51,.88), rgba(10,22,37,.88));
    margin-bottom: 12px;
}

.student-avatar {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(59,130,246,.12);
    font-size: 19px;
}

.student-name {
    font-size: 14px;
    font-weight: 700;
    color: #f8fafc;
}

.student-id {
    color: #71839b;
    font-size: 11px;
    margin-top: 2px;
}

.present-pill {
    display: inline-block;
    color: #86efac;
    background: rgba(34,197,94,.10);
    border: 1px solid rgba(34,197,94,.18);
    border-radius: 999px;
    padding: 4px 8px;
    font-size: 10px;
    font-weight: 700;
}

.absent-pill {
    display: inline-block;
    color: #fca5a5;
    background: rgba(239,68,68,.10);
    border: 1px solid rgba(239,68,68,.18);
    border-radius: 999px;
    padding: 4px 8px;
    font-size: 10px;
    font-weight: 700;
}

/* Buttons */
.stButton > button {
    border-radius: 10px !important;
    border: 1px solid rgba(148,163,184,.14) !important;
    font-weight: 600 !important;
    min-height: 42px;
    transition: all .2s ease !important;
}

.stButton > button:hover {
    border-color: rgba(96,165,250,.4) !important;
    transform: translateY(-1px);
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    border: none !important;
    box-shadow: 0 8px 22px rgba(37,99,235,.22);
}

/* Inputs */
.stTextInput input,
.stSelectbox div[data-baseweb="select"],
.stFileUploader section {
    border-radius: 11px !important;
}

.stTextInput input {
    background: rgba(255,255,255,.025) !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    border: 1px dashed rgba(96,165,250,.25);
    border-radius: 16px;
    padding: 7px;
    background: rgba(59,130,246,.025);
}

/* Tables */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
}

/* Progress */
div[data-testid="stProgressBar"] > div {
    border-radius: 99px;
}

/* Footer */
.footer {
    margin-top: 70px;
    padding: 28px 0 10px;
    border-top: 1px solid var(--border);
    color: #64748b;
    font-size: 11px;
}

.footer-brand {
    color: #cbd5e1;
    font-weight: 700;
    font-size: 13px;
}

.footer-right {
    text-align: right;
}

/* Alerts */
div[data-testid="stAlert"] {
    border-radius: 12px !important;
}

/* Mobile */
@media (max-width: 900px) {
    .hero {
        padding: 28px;
    }

    .hero h1 {
        font-size: 34px;
    }

    .page-title {
        font-size: 25px;
    }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================

if "selection" not in st.session_state:
    st.session_state.selection = "Home"

if "uploaded_students" not in st.session_state:
    st.session_state.uploaded_students = []

if "attendance_map" not in st.session_state:
    st.session_state.attendance_map = {}

if "last_sync" not in st.session_state:
    st.session_state.last_sync = None


def go_to(section):
    st.session_state.selection = section


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-icon">📊</div>
        <div>
            <div class="brand-name">AttendX</div>
            <div class="brand-subtitle">SMART ATTENDANCE PLATFORM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-label">WORKSPACE</div>', unsafe_allow_html=True)

    navigation_options = [
        "Home",
        "Student Management",
        "Mark Attendance",
        "View Reports",
        "Analytics",
    ]

    current_index = navigation_options.index(st.session_state.selection)

    selected_navigation = st.radio(
        "Navigation",
        navigation_options,
        index=current_index,
        label_visibility="collapsed",
    )

    if selected_navigation != st.session_state.selection:
        st.session_state.selection = selected_navigation
        st.rerun()

    st.markdown("---")

    total_students = len(st.session_state.uploaded_students)
    present_count = list(st.session_state.attendance_map.values()).count("Present")

    st.markdown(
        f"""
        <div class="sidebar-bottom">
            <div class="sidebar-status">
                <span class="status-dot"></span>
                System operational
            </div>
            <div style="margin-top:12px;color:#71839b;font-size:11px;">
                {total_students} students loaded
                · {present_count} present today
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# TOP BAR
# ============================================================

now = datetime.now()

st.markdown(
    f"""
    <div class="topbar">
        <div class="topbar-left">
            <small>{now.strftime("%A, %d %B %Y")}</small>
            <strong>Attendance Management Workspace</strong>
        </div>
        <div class="profile-chip">
            <div class="avatar">G</div>
            <div>
                <div style="font-weight:700;color:#e2e8f0;">Administrator</div>
                <div style="font-size:10px;color:#64748b;">AttendX Admin</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HOME
# ============================================================

if st.session_state.selection == "Home":

    st.markdown(
        """
        <div class="hero">
            <div class="hero-grid"></div>
            <span class="hero-badge">✦ SMART ATTENDANCE PLATFORM</span>
            <h1>Attendance,<br><span style="color:#60a5fa;">simplified.</span></h1>
            <p>
                Manage students, record attendance, generate reports and
                understand classroom performance from one modern workspace.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    if st.button("🚀  Get Started", type="primary", use_container_width=True):
        st.session_state.selection = "Student Management"
        st.rerun()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)

    features = [
        (
            "👥",
            "Student Management",
            "Import and manage your complete student list with a clean workflow.",
        ),
        (
            "✓",
            "Fast Attendance",
            "Mark Present or Absent in seconds using a focused attendance workspace.",
        ),
        (
            "📈",
            "Smart Insights",
            "Track attendance patterns and turn daily records into useful reports.",
        ),
    ]

    for col, (icon, title, desc) in zip([f1, f2, f3], features):
        with col:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Quick overview on home
    total = len(st.session_state.uploaded_students)
    present = list(st.session_state.attendance_map.values()).count("Present")
    absent = max(total - present, 0)
    rate = (present / total * 100) if total else 0

    st.markdown(
        '<div class="section-card"><div class="section-title">Today at a glance</div>'
        '<div class="section-subtitle">Your current attendance workspace</div></div>',
        unsafe_allow_html=True,
    )

    h1, h2, h3, h4 = st.columns(4)

    home_metrics = [
        ("👥", "Students", total, "Total loaded"),
        ("✓", "Present", present, "Marked today"),
        ("✕", "Absent", absent, "Marked today"),
        ("◔", "Attendance", f"{rate:.1f}%", "Current rate"),
    ]

    for col, (icon, label, value, note) in zip([h1, h2, h3, h4], home_metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon">{icon}</div>
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# STUDENT MANAGEMENT
# ============================================================

elif st.session_state.selection == "Student Management":

    st.markdown('<div class="page-kicker">Workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Student Management</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-description">Import your student roster and prepare it for attendance tracking.</div>',
        unsafe_allow_html=True,
    )

    total = len(st.session_state.uploaded_students)

    c1, c2, c3 = st.columns(3)

    for col, icon, label, value, note in [
        (c1, "👥", "Students", total, "Currently loaded"),
        (c2, "✓", "Present", list(st.session_state.attendance_map.values()).count("Present"), "Current session"),
        (c3, "↻", "Last sync", st.session_state.last_sync.strftime("%H:%M") if st.session_state.last_sync else "Not synced", "Attendance records"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon">{icon}</div>
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Import student roster</div>
            <div class="section-subtitle">
                Upload a CSV containing your student details. Recommended columns:
                student_id, name, gender.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=["csv"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)

            st.markdown(
                f"""
                <div style="margin:14px 0 10px;color:#cbd5e1;font-size:13px;font-weight:600;">
                    Preview · {len(df)} students detected
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.dataframe(df, use_container_width=True, hide_index=True)

            if st.button("✓  Confirm & Import Students", type="primary", use_container_width=True):
                required_columns = {"student_id", "name"}

                if not required_columns.issubset(set(df.columns)):
                    missing = ", ".join(sorted(required_columns - set(df.columns)))
                    st.error(f"Missing required column(s): {missing}")
                else:
                    st.session_state.uploaded_students = df.to_dict("records")
                    st.session_state.attendance_map = {
                        s["student_id"]: "Absent"
                        for s in st.session_state.uploaded_students
                    }
                    st.success(
                        f"Successfully imported {len(st.session_state.uploaded_students)} students."
                    )
                    st.rerun()

        except Exception as e:
            st.error(f"Unable to read the CSV file: {e}")

    if st.session_state.uploaded_students:
        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

        with st.expander("View imported student list"):
            current_df = pd.DataFrame(st.session_state.uploaded_students)
            st.dataframe(current_df, use_container_width=True, hide_index=True)


# ============================================================
# MARK ATTENDANCE
# ============================================================

elif st.session_state.selection == "Mark Attendance":

    st.markdown('<div class="page-kicker">Daily workflow</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Mark Attendance</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-description">Quickly update attendance and sync today’s records.</div>',
        unsafe_allow_html=True,
    )

    students = st.session_state.uploaded_students

    if not students:
        st.markdown(
            """
            <div class="section-card" style="text-align:center;padding:45px;">
                <div style="font-size:42px;">👥</div>
                <div style="font-size:18px;font-weight:700;margin-top:12px;">
                    No students yet
                </div>
                <div style="color:#71839b;font-size:12px;margin-top:7px;">
                    Import your student roster before marking attendance.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Go to Student Management", type="primary"):
            go_to("Student Management")
            st.rerun()

    else:
        total = len(students)
        present = list(st.session_state.attendance_map.values()).count("Present")
        absent = total - present
        rate = (present / total * 100) if total else 0

        m1, m2, m3, m4 = st.columns(4)

        metrics = [
            ("👥", "Total Students", total, "Roster"),
            ("✓", "Present", present, "Marked present"),
            ("✕", "Absent", absent, "Marked absent"),
            ("◔", "Attendance Rate", f"{rate:.1f}%", "Today"),
        ]

        for col, (icon, label, value, note) in zip([m1, m2, m3, m4], metrics):
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-icon">{icon}</div>
                        <div class="metric-label">{label}</div>
                        <div class="metric-value">{value}</div>
                        <div class="metric-note">{note}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        search_col, filter_col = st.columns([2, 1])

        with search_col:
            search = st.text_input(
                "Search",
                placeholder="🔍  Search by student name or ID...",
                label_visibility="collapsed",
            )

        with filter_col:
            status_filter = st.selectbox(
                "Filter",
                ["All Students", "Present", "Absent"],
                label_visibility="collapsed",
            )

        filtered = []

        search_lower = search.lower().strip()

        for student in students:
            name = str(student.get("name", ""))
            sid = str(student.get("student_id", ""))
            current_status = st.session_state.attendance_map.get(
                student["student_id"], "Absent"
            )

            matches_search = (
                not search_lower
                or search_lower in name.lower()
                or search_lower in sid.lower()
            )

            matches_filter = (
                status_filter == "All Students"
                or current_status == status_filter
            )

            if matches_search and matches_filter:
                filtered.append(student)

        st.caption(f"Showing {len(filtered)} of {total} students")

        cols = st.columns(3)

        for idx, student in enumerate(filtered):
            with cols[idx % 3]:
                student_id = student["student_id"]
                current_status = st.session_state.attendance_map.get(
                    student_id, "Absent"
                )

                gender = str(student.get("gender", "")).strip().lower()
                emoji = "👨‍🎓" if gender in ["male", "m", "boy"] else "👩‍🎓"

                pill = (
                    '<span class="present-pill">● PRESENT</span>'
                    if current_status == "Present"
                    else '<span class="absent-pill">● ABSENT</span>'
                )

                st.markdown(
                    f"""
                    <div class="student-card">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <div class="student-avatar">{emoji}</div>
                            <div style="flex:1;">
                                <div class="student-name">{student["name"]}</div>
                                <div class="student-id">{student_id}</div>
                            </div>
                            {pill}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                status = st.segmented_control(
                    "Attendance status",
                    ["Present", "Absent"],
                    key=f"st_{student_id}",
                    default=current_status,
                    label_visibility="collapsed",
                )

                if status:
                    st.session_state.attendance_map[student_id] = status

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        if st.button("💾  Save Attendance", type="primary", use_container_width=True):
            save_attendance(st.session_state.attendance_map)
            st.session_state.last_sync = datetime.now()
            st.success("Attendance records synced successfully.")


# ============================================================
# REPORTS
# ============================================================

elif st.session_state.selection == "View Reports":

    st.markdown('<div class="page-kicker">Insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Attendance Reports</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-description">Review attendance records across different reporting periods.</div>',
        unsafe_allow_html=True,
    )

    students = st.session_state.uploaded_students

    if not students:
        st.info("Import students first to generate reports.")
    else:
        present = list(st.session_state.attendance_map.values()).count("Present")
        total = len(students)
        rate = (present / total * 100) if total else 0

        r1, r2, r3 = st.columns(3)

        for col, icon, label, value, note in [
            (r1, "👥", "Students", total, "Total roster"),
            (r2, "✓", "Present today", present, "Current attendance"),
            (r3, "◔", "Attendance rate", f"{rate:.1f}%", "Today"),
        ]:
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-icon">{icon}</div>
                        <div class="metric-label">{label}</div>
                        <div class="metric-value">{value}</div>
                        <div class="metric-note">{note}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(
            ["Today", "Monthly Summary", "Yearly Overview"]
        )

        def get_rep(days):
            lst = []
            for s in students:
                pre = np.random.randint(0, days + 1)
                perc = (pre / days) * 100 if days > 0 else 0

                lst.append(
                    {
                        "Name": s["name"],
                        "ID": s["student_id"],
                        "Days Present": f"{pre}/{days}",
                        "Attendance %": f"{perc:.1f}%",
                    }
                )

            return pd.DataFrame(lst)

        with tab1:
            today_df = pd.DataFrame(
                [
                    {
                        "Name": s["name"],
                        "Student ID": s["student_id"],
                        "Status": st.session_state.attendance_map.get(
                            s["student_id"], "Absent"
                        ),
                    }
                    for s in students
                ]
            )

            st.dataframe(
                today_df,
                use_container_width=True,
                hide_index=True,
            )

        with tab2:
            st.dataframe(
                get_rep(22),
                use_container_width=True,
                hide_index=True,
            )

        with tab3:
            st.dataframe(
                get_rep(220),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# ANALYTICS
# ============================================================

elif st.session_state.selection == "Analytics":

    st.markdown('<div class="page-kicker">Performance</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-description">Understand your current attendance performance at a glance.</div>',
        unsafe_allow_html=True,
    )

    students = st.session_state.uploaded_students

    if not students:
        st.markdown(
            """
            <div class="section-card" style="text-align:center;padding:45px;">
                <div style="font-size:42px;">📈</div>
                <div style="font-size:18px;font-weight:700;margin-top:12px;">
                    Analytics will appear here
                </div>
                <div style="color:#71839b;font-size:12px;margin-top:7px;">
                    Import students and mark attendance to populate your dashboard.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        total = len(students)
        present = list(st.session_state.attendance_map.values()).count("Present")
        absent = total - present
        rate = (present / total * 100) if total else 0

        a1, a2, a3, a4 = st.columns(4)

        analytics_metrics = [
            ("👥", "Total", total, "Students"),
            ("✓", "Present", present, "Today"),
            ("✕", "Absent", absent, "Today"),
            ("◔", "Rate", f"{rate:.1f}%", "Attendance"),
        ]

        for col, (icon, label, value, note) in zip(
            [a1, a2, a3, a4], analytics_metrics
        ):
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-icon">{icon}</div>
                        <div class="metric-label">{label}</div>
                        <div class="metric-value">{value}</div>
                        <div class="metric-note">{note}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        chart_col, insight_col = st.columns([1.6, 1])

        with chart_col:
            st.markdown(
                """
                <div class="section-card">
                    <div class="section-title">Today's attendance distribution</div>
                    <div class="section-subtitle">Present vs absent students</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            chart_df = pd.DataFrame(
                {
                    "Status": ["Present", "Absent"],
                    "Students": [present, absent],
                }
            )

            st.bar_chart(
                chart_df,
                x="Status",
                y="Students",
                use_container_width=True,
            )

        with insight_col:
            st.markdown(
                f"""
                <div class="section-card">
                    <div class="section-title">Attendance health</div>
                    <div class="section-subtitle">Current classroom signal</div>
                    <div style="font-size:38px;font-weight:800;margin-top:20px;">
                        {rate:.1f}%
                    </div>
                    <div style="color:#8fa1b8;font-size:12px;margin:5px 0 15px;">
                        Current attendance rate
                    </div>
                """,
                unsafe_allow_html=True,
            )

            st.progress(min(rate / 100, 1.0))

            if rate >= 85:
                message = "Excellent attendance performance."
                icon = "🟢"
            elif rate >= 75:
                message = "Attendance is in a healthy range."
                icon = "🟡"
            else:
                message = "Attendance needs attention."
                icon = "🔴"

            st.markdown(
                f"""
                    <div style="margin-top:14px;padding:12px;border-radius:11px;
                    background:rgba(255,255,255,.025);color:#cbd5e1;font-size:12px;">
                        {icon} {message}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Student-level snapshot
        snapshot = []

        for student in students:
            sid = student["student_id"]
            status = st.session_state.attendance_map.get(sid, "Absent")
            snapshot.append(
                {
                    "Student": student["name"],
                    "Student ID": sid,
                    "Today's Status": status,
                }
            )

        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Student status snapshot</div>
                <div class="section-subtitle">Live attendance state for the current session</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.dataframe(
            pd.DataFrame(snapshot),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# GLOBAL FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        <div style="display:flex;justify-content:space-between;gap:20px;">
            <div>
                <div class="footer-brand">AttendX</div>
                <div style="margin-top:5px;">
                    Smart attendance. Simple insights.
                </div>
            </div>
            <div class="footer-right">
                <div>Product UI v1.0</div>
                <div style="margin-top:5px;">© 2026 AttendX</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
