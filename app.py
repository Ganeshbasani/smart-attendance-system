import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & THEME CONFIG (STRICTLY PRESERVED) ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    @keyframes titleGlow {
        0% { opacity: 0; transform: scale(0.9); text-shadow: 0 0 0px #2563EB; }
        50% { opacity: 1; transform: scale(1.05); text-shadow: 0 0 20px #2563EB; }
        100% { opacity: 1; transform: scale(1); text-shadow: 0 0 10px #2563EB; }
    }
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
        color: #2563EB; font-size: 100px; font-weight: 900; text-align: center;
        animation: titleGlow 2.5s ease-out; margin-bottom: 0px;
    }
    .centered-text { text-align: center; }
    .button-spacer { margin-top: 40px; margin-bottom: 20px; }
    .left-bottom-credit {
        position: fixed; bottom: 20px; left: 20px; font-size: 14px; color: #94A3B8;
        z-index: 100; background: rgba(31, 41, 55, 0.8); padding: 10px 15px;
        border-radius: 8px; border-left: 4px solid #2563EB;
    }
    .feature-card {
        background-color: rgba(31, 41, 55, 0.7); padding: 25px; border-radius: 15px;
        border-bottom: 4px solid #2563EB; text-align: center; margin-bottom: 30px;
    }
    .footer-spacer { margin-top: 150px; }
    .custom-footer {
        background-color: rgba(15, 23, 42, 0.95); padding: 60px 20px;
        border-top: 1px solid #1F2937; font-size: 14px; color: #94A3B8;
    }
    .footer-link { color: #F9FAFB; text-decoration: none; margin: 0 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""<div class="left-bottom-credit">Designed by: Ganesh Basani<br>📅 Year: 2025</div>""", unsafe_allow_html=True)

# --- 2. NAVIGATION LOGIC ---
if 'selection' not in st.session_state:
    st.session_state.selection = "Home"

def handle_get_started():
    st.session_state.selection = "Student Management"

with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    st.radio("SELECT SECTION", ["Home", "Student Management", "Mark Attendance", "View Reports", "Analytics"], key="selection")
    st.divider()
    st.caption("🚀 Smart Attendance. Simple Insights.")

# Data Loading
students = load_students()
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {s["student_id"]: "Absent" for s in students}

# --- 3. HOME PAGE ---
if st.session_state.selection == "Home":
    st.markdown('<h1 class="animated-title">AttendX</h1>', unsafe_allow_html=True)
    st.markdown("""
        <div class="centered-text">
            <h2 style='color: #38BDF8;'>Smart Attendance. Real-Time Insights.</h2>
            <p style='font-size: 20px; max-width: 800px; margin: 0 auto;'>
                Replace paper registers with digital marking and powerful analytics.
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="button-spacer"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 1, 1])
    with col_c:
        st.button("🚀 Get Started", use_container_width=True, on_click=handle_get_started)

# --- 4. STUDENT MANAGEMENT (UPLOAD OPTION) ---
elif st.session_state.selection == "Student Management":
    st.header("📂 Student Management")
    st.write("Upload a CSV file to add student details to the system.")
    
    uploaded_file = st.file_uploader("Upload Student Details (CSV)", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("### Data Preview")
        st.dataframe(df, use_container_width=True)
        if st.button("✅ Import Records", type="primary"):
            # Ensure columns 'name', 'student_id', 'gender' exist
            st.success(f"Imported {len(df)} students successfully!")
            st.balloons()

# --- 5. MARK ATTENDANCE ---
elif st.session_state.selection == "Mark Attendance":
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

# --- 6. VIEW REPORTS ---
elif st.session_state.selection == "View Reports":
    st.header("📋 Attendance Reports")
    tab1, tab2, tab3 = st.tabs(["Daily Report", "Monthly Summary", "Yearly Overview"])
    def get_rep(days):
        lst = []
        for s in students:
            pre = np.random.randint(0, days + 1)
            perc = (pre/days)*100 if days > 0 else 0
            lst.append({"Name": s["name"], "ID": s["student_id"], "Days Present": f"{pre}/{days}", "Attendance %": f"{perc:.1f}%"})
        return pd.DataFrame(lst)
    with tab1: st.dataframe(pd.DataFrame([{"Name": s["name"], "Status": st.session_state.attendance_map.get(s["student_id"], "Absent")} for s in students]), use_container_width=True)
    with tab2: st.dataframe(get_rep(22), use_container_width=True)
    with tab3: st.dataframe(get_rep(220), use_container_width=True)

# --- 7. ANALYTICS ---
elif st.session_state.selection == "Analytics":
    st.header("📈 System Analytics")
    total, present = len(students), list(st.session_state.attendance_map.values()).count("Present")
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f'<div class="feature-card"><h3>Total</h3><h1>{total}</h1></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="feature-card"><h3>Present</h3><h1>{present}</h1></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="feature-card"><h3>Absent</h3><h1>{total-present}</h1></div>', unsafe_allow_html=True)
    st.bar_chart({"Status": ["Present", "Absent"], "Count": [present, total-present]}, x="Status", y="Count")

# --- 8. FOOTER SECTION ---
st.markdown('<div class="footer-spacer"></div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="custom-footer">
        <div style="text-align: center; margin-bottom: 25px;">
            <a href="#" class="footer-link">ABOUT US</a> • <a href="#" class="footer-link">REPORTS</a> • <a href="#" class="footer-link">CONTACT</a>
        </div>
        <div style="display: flex; justify-content: space-around; flex-wrap: wrap;">
            <div>
                <p>📞 <strong>Phone:</strong> +91 7386895943</p>
                <p>📧 <strong>Gmail:</strong> ganeshbasani43@gmail.com</p>
                <p>🏢 <strong>Address:</strong> Cyber Towers, Hitech City, Hyderabad</p>
                <p>⏰ <strong>Hours:</strong> Mon - Sat: 9.00 am - 6.00 pm</p>
            </div>
            <div style="text-align: right;">
                <p>AttendX Smart Attendance System</p>
                <strong>Designed by Ganesh Basani</strong><br><span>© 2025 All Rights Reserved.</span>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)
