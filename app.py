import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & THEME CONFIG (STRICTLY KEPT) ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* ADDED: Biometric Transparent Background Overlay */
    .stApp {
        background: linear-gradient(rgba(11, 17, 32, 0.85), rgba(11, 17, 32, 0.85)), 
                    url('https://www.transparenttextures.com/patterns/carbon-fibre.png'),
                    url('https://img.icons8.com/ios/452/fingerprint.png'); 
        background-repeat: repeat, repeat, no-repeat;
        background-position: center;
        background-attachment: fixed;
        background-color: #0B1120;
        color: #F9FAFB;
    }
    
    .animated-title {
        color: #2563EB; font-size: 85px; font-weight: 900; text-align: center;
        animation: fadeIn 2s ease-in-out; margin-bottom: 0px;
    }
    .centered-text { text-align: center; margin-bottom: 30px; }
    
    .feature-card {
        background-color: rgba(31, 41, 55, 0.7); padding: 25px; border-radius: 15px;
        border-bottom: 4px solid #2563EB; text-align: center;
    }

    /* ADDED: Spacer to push footer further down */
    .footer-spacer { margin-top: 150px; }

    .custom-footer {
        background-color: rgba(15, 23, 42, 0.9); padding: 40px 20px;
        border-top: 1px solid #1F2937; font-size: 14px; color: #94A3B8;
    }
    .footer-link { color: #F9FAFB; text-decoration: none; margin: 0 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAVIGATION LOGIC (STOPS CALLBACK LOOP) ---
if 'page' not in st.session_state:
    st.session_state.page = "Home"

# Logic for "Get Started" Redirect
def handle_get_started():
    st.session_state.page = "Mark Attendance"

with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    nav_list = ["Home", "Mark Attendance", "View Reports", "Analytics"]
    current_index = nav_list.index(st.session_state.page)
    
    choice = st.radio("SELECT SECTION", nav_list, index=current_index, key="sidebar_selection")
    
    if choice != st.session_state.page:
        st.session_state.page = choice
        st.rerun()

    st.divider()
    st.caption(f"**Designed by:** Ganesh Basani")
    st.caption("📅 **Year:** 2025")

students = load_students()
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {s["student_id"]: "Absent" for s in students}

# --- 3. HOME PAGE ---
if st.session_state.page == "Home":
    st.markdown('<h1 class="animated-title">AttendX</h1>', unsafe_allow_html=True)
    st.markdown("""
        <div class="centered-text">
            <h2 style='color: #38BDF8;'>Smart Attendance. Real-Time Insights.</h2>
            <p style='font-size: 18px; max-width: 800px; margin: 0 auto;'>
                Replace paper registers with digital marking and powerful analytics.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
        # FIXED: Use on_click to redirect correctly
        st.button("🚀 Get Started", use_container_width=True, on_click=handle_get_started)

    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    features = [("📱 Digital Marking", "Mark attendance instantly."), 
                ("📊 Smart Reports", "Generate automated insights."), 
                ("🏷️ Auto-Grading", "Intelligent A-D grading.")]
    for i, (title, desc) in enumerate(features):
        with [f1, f2, f3][i]:
            st.markdown(f'<div class="feature-card"><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)

# --- 4. MARK ATTENDANCE ---
elif st.session_state.page == "Mark Attendance":
    st.header("📝 Mark Attendance")
    search = st.text_input("🔍 Search Student", placeholder="Search by name...")
    cols = st.columns(3)
    filtered = [s for s in students if search.lower() in s["name"].lower()]
    for idx, student in enumerate(filtered):
        with cols[idx % 3]:
            with st.container(border=True):
                gender = str(student.get("gender", "")).strip().lower()
                emoji = "👦" if gender in ["male", "m", "boy"] else "👧"
                st.markdown(f"### {emoji} {student['name']}")
                status = st.segmented_control("Status", ["Present", "Absent"], 
                                             key=f"st_{student['student_id']}", 
                                             default=st.session_state.attendance_map.get(student["student_id"], "Absent"))
                st.session_state.attendance_map[student["student_id"]] = status
    if st.button("💾 Save Attendance", type="primary", use_container_width=True):
        save_attendance(st.session_state.attendance_map)
        st.success("Records Synced Successfully!")

# --- 5. VIEW REPORTS ---
elif st.session_state.page == "View Reports":
    st.header("📋 Attendance Reports")
    tab1, tab2, tab3 = st.tabs(["Daily Report", "Monthly Summary", "Yearly Overview"])
    report_data = []
    for s in students:
        status = st.session_state.attendance_map.get(s["student_id"], "Absent")
        perc = 100 if status == "Present" else 0
        grade = "A" if perc >= 90 else "B" if perc >= 80 else "C" if perc >= 70 else "D"
        report_data.append({"Student Name": s["name"], "ID": s["student_id"], "Status": status, "Attendance %": f"{perc}%", "Grade": grade})
    df_report = pd.DataFrame(report_data)
    with tab1: st.dataframe(df_report, use_container_width=True)
    with tab2: st.write(df_report)
    with tab3: st.write(df_report)

# --- 6. ANALYTICS ---
elif st.session_state.page == "Analytics":
    st.header("📈 System Analytics")
    total = len(students)
    present = list(st.session_state.attendance_map.values()).count("Present")
    rate = (present / total) * 100 if total > 0 else 0
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f'<div class="feature-card"><h3>Total</h3><h1 style="color:#2563EB;">{total}</h1></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="feature-card"><h3>Present</h3><h1 style="color:#22C55E;">{present}</h1></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="feature-card"><h3>Rate</h3><h1 style="color:#F97316;">{rate:.1f}%</h1></div>', unsafe_allow_html=True)

# --- 7. FOOTER SECTION (KEPT EXACT DETAILS) ---
st.markdown('<div class="footer-spacer"></div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="custom-footer">
        <div style="text-align: center; margin-bottom: 20px;">
            <a href="#" class="footer-link">ABOUT US</a> • <a href="#" class="footer-link">CONTACT</a> • <a href="#" class="footer-link">TERMS</a>
        </div>
        <div style="display: flex; justify-content: space-around; flex-wrap: wrap;">
            <div>
                <p>📞 +91 7386895943</p>
                <p>📍 Cyber Towers, Hitech City, Hyderabad</p>
                <p>📧 ganeshbasani43@gmail.com</p>
            </div>
            <div style="text-align: right;">
                <p>Smart Attendance. Real-Time Insights.</p>
                <strong>Designed by Ganesh Basani</strong>
            </div>
        </div>
        <p style="text-align: center; margin-top:20px;">© 2025 AttendX Smart Attendance System.</p>
    </div>
""", unsafe_allow_html=True)
