import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & THEME CONFIG ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

# (Keep your existing CSS here...)
st.markdown("""
    <style>
    .stApp { background-color: #0B1120; color: #F9FAFB; }
    .animated-title { color: #2563EB; font-size: 85px; font-weight: 900; text-align: center; margin-bottom: 0px; }
    .feature-card { background-color: rgba(31, 41, 55, 0.7); padding: 25px; border-radius: 15px; border-bottom: 4px solid #2563EB; text-align: center; }
    .custom-footer { background-color: rgba(15, 23, 42, 0.9); padding: 40px 20px; border-top: 1px solid #1F2937; font-size: 14px; color: #94A3B8; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAVIGATION LOGIC (THE FIX) ---
# Initialize the page state if it doesn't exist
if 'page' not in st.session_state:
    st.session_state.page = "Home"

# Function to handle button clicks from the Home page
def change_page(page_name):
    st.session_state.page = page_name

# Sidebar Navigation
with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    
    # We map the options to their index to keep the radio in sync
    nav_options = ["Home", "Mark Attendance", "View Reports", "Analytics"]
    
    # The key="nav_radio" ensures the radio button is tracked uniquely
    choice = st.radio(
        "SELECT SECTION", 
        nav_options, 
        index=nav_options.index(st.session_state.page),
        key="sidebar_nav"
    )
    
    # If the user clicks the radio, update the session state
    if choice != st.session_state.page:
        st.session_state.page = choice
        st.rerun()

    st.divider()
    st.caption(f"**Designed by:** Ganesh Basani")
    st.caption("📅 **Year:** 2025")

# Load Students Data
students = load_students()
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {s["student_id"]: "Absent" for s in students}

# --- 3. HOME PAGE ---
if st.session_state.page == "Home":
    st.markdown('<h1 class="animated-title">AttendX</h1>', unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h2 style='color: #38BDF8;'>Smart Attendance. Real-Time Insights.</h2>
            <p style='font-size: 18px; max-width: 800px; margin: 0 auto;'>
                Replace paper registers with digital marking and powerful analytics.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
        # Use on_click to change page smoothly
        if st.button("🚀 Get Started", use_container_width=True, on_click=change_page, args=("Mark Attendance",)):
            st.rerun()

# --- 4. MARK ATTENDANCE ---
elif st.session_state.page == "Mark Attendance":
    st.header("📝 Mark Attendance")
    # ... (Keep your Mark Attendance logic here)
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
        st.success("Records Synced!")

# --- 5. VIEW REPORTS ---
elif st.session_state.page == "View Reports":
    st.header("📋 Attendance Reports")
    # ... (Keep your Reports Logic here)
    report_data = [{"Student Name": s["name"], "ID": s["student_id"], "Status": st.session_state.attendance_map.get(s["student_id"], "Absent")} for s in students]
    st.dataframe(pd.DataFrame(report_data), use_container_width=True)

# --- 6. ANALYTICS ---
elif st.session_state.page == "Analytics":
    st.header("📈 System Analytics")
    total = len(students)
    present = list(st.session_state.attendance_map.values()).count("Present")
    rate = (present / total) * 100 if total > 0 else 0
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f'<div class="feature-card"><h3>Total</h3><h1>{total}</h1></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="feature-card"><h3>Present</h3><h1>{present}</h1></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="feature-card"><h3>Rate</h3><h1>{rate:.1f}%</h1></div>', unsafe_allow_html=True)

# --- 7. FOOTER ---
st.markdown("<br><br>", unsafe_allow_html=True)
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
                <p>Smart Attendance. Simple Insights.</p>
                <strong>Designed by Ganesh Basani</strong>
            </div>
        </div>
        <p style="text-align: center; margin-top:20px;">© 2025 AttendX Smart Attendance System.</p>
    </div>
""", unsafe_allow_html=True)
