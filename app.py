import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & THEME CONFIG ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

# Advanced CSS for Animations, Transparency, and Branding
st.markdown("""
    <style>
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stApp {
        background: linear-gradient(rgba(11, 17, 32, 0.8), rgba(11, 17, 32, 0.8)), 
                    url('https://www.transparenttextures.com/patterns/carbon-fibre.png');
        background-color: #0B1120;
        color: #F9FAFB;
    }
    
    .animated-title {
        color: #2563EB;
        font-size: 85px;
        font-weight: 900;
        text-align: center;
        animation: fadeIn 2s ease-in-out;
        margin-bottom: 0px;
    }
    
    .centered-text {
        text-align: center;
        margin-bottom: 30px;
    }
    
    .feature-card {
        background-color: rgba(31, 41, 55, 0.7);
        padding: 25px;
        border-radius: 15px;
        border-bottom: 4px solid #2563EB;
        text-align: center;
    }

    /* Footer Styling based on Reference */
    .custom-footer {
        background-color: rgba(15, 23, 42, 0.9);
        padding: 40px 20px;
        border-top: 1px solid #1F2937;
        font-size: 14px;
        color: #94A3B8;
    }
    .footer-link { color: #F9FAFB; text-decoration: none; margin: 0 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAVIGATION & STATE ---
if 'page' not in st.session_state:
    st.session_state.page = "Home"

def nav_to(page_name):
    st.session_state.page = page_name

with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    st.session_state.page = st.radio("SELECT SECTION", ["Home", "Mark Attendance", "View Reports", "Analytics"], 
                                    index=["Home", "Mark Attendance", "View Reports", "Analytics"].index(st.session_state.page))
    st.divider()
    st.caption(f"**Designed by:** Ganesh Basani")
    st.caption("📅 **Year:** 2025")

# Load Real Data
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
                Experience seamless tracking and automated reporting in one place.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Redirect Button
    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
        if st.button("🚀 Get Started", use_container_width=True):
            nav_to("Mark Attendance")
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    features = [("📱 Digital Marking", "Fast and secure marking."), 
                ("📊 Smart Reports", "Deep data analytics."), 
                ("🏷️ Auto-Grading", "Performance based grading.")]
    
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

    if st.button("💾 Save Attendance", type="primary"):
        save_attendance(st.session_state.attendance_map)
        st.success("Records Synced!")
        st.balloons()

# --- 5. ANALYTICS (FIXED MISTAKE) ---
elif st.session_state.page == "Analytics":
    st.header("📈 Attendance Analytics")
    
    # Using Session State to ensure charts reflect current selections
    df_analytics = pd.DataFrame([
        {"Student": s["name"], "Status": st.session_state.attendance_map[s["student_id"]]}
        for s in students
    ])
    
    if not df_analytics.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Presence vs Absence")
            counts = df_analytics["Status"].value_counts()
            st.bar_chart(counts)
        with c2:
            st.write("### Attendance Percentage")
            # Logic for a single session: 100% if Present, 0% if Absent
            df_analytics["Score"] = df_analytics["Status"].apply(lambda x: 100 if x == "Present" else 0)
            st.line_chart(df_analytics.set_index("Student")["Score"])
    else:
        st.warning("No data available to visualize.")

# --- 6. FOOTER (REDESIGNED) ---
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(f"""
    <div class="custom-footer">
        <div style="text-align: center; margin-bottom: 20px;">
            <a href="#" class="footer-link">ABOUT US</a> • 
            <a href="#" class="footer-link">REPORTS</a> • 
            <a href="#" class="footer-link">CONTACT</a> • 
            <a href="#" class="footer-link">PRIVACY POLICY</a>
        </div>
        <div style="display: flex; justify-content: space-around; flex-wrap: wrap;">
            <div>
                <p>📞 +91 7386895943</p>
                <p>📍 Cyber Towers, Hitech City, Hyderabad</p>
                <p>📧 ganeshbasani43@gmail.com</p>
                <p>⏰ Mon - Sat: 9.00 am - 6.00 pm</p>
            </div>
            <div style="max-width: 400px; text-align: right;">
                <p>AttendX is a state-of-the-art solution designed to bridge the gap between 
                traditional record-keeping and modern data analytics. Built for accuracy, 
                efficiency, and simplicity.</p>
                <strong>Designed by Ganesh Basani</strong>
            </div>
        </div>
        <hr style="border-color: #1F2937;">
        <p style="text-align: center;">© 2025 AttendX Smart Attendance System. All rights reserved.</p>
    </div>
""", unsafe_allow_html=True)
