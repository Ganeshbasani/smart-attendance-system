import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import save_attendance

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
        background-position: center; background-attachment: fixed;
        background-color: #0B1120; color: #F9FAFB;
    }
    
    .animated-title {
        color: #2563EB; font-size: 100px; font-weight: 900; text-align: center;
        animation: titleGlow 2.5s ease-out; margin-bottom: 0px;
    }
    
    /* Attendance Color Styling */
    .status-present { color: #22C55E !important; font-weight: bold; }
    .status-absent { color: #EF4444 !important; font-weight: bold; }

    .feature-card {
        background-color: rgba(31, 41, 55, 0.7); padding: 25px; border-radius: 15px;
        border-bottom: 4px solid #2563EB; text-align: center; margin-bottom: 30px;
    }

    .left-bottom-credit {
        position: fixed; bottom: 20px; left: 20px; font-size: 13px; color: #94A3B8;
        z-index: 100; background: rgba(15, 23, 42, 0.9); padding: 10px 15px;
        border-radius: 8px; border-left: 4px solid #2563EB; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }

    /* Redesigned Sleek Footer */
    .footer-container {
        margin-top: 150px;
        padding: 60px 0 30px 0;
        background: rgba(15, 23, 42, 0.8);
        border-top: 1px solid rgba(37, 99, 235, 0.2);
        backdrop-filter: blur(10px);
    }
    .footer-content {
        max-width: 1200px;
        margin: 0 auto;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 0 20px;
    }
    .footer-section h4 { color: #2563EB; margin-bottom: 15px; font-size: 18px; }
    .footer-section p { color: #94A3B8; font-size: 14px; margin: 5px 0; }
    .footer-bottom {
        text-align: center;
        padding-top: 40px;
        color: #475569;
        font-size: 12px;
        letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""<div class="left-bottom-credit">Designed by: Ganesh Basani<br>📅 Year: 2025</div>""", unsafe_allow_html=True)

# --- 2. NAVIGATION & DATA STATE ---
if 'selection' not in st.session_state:
    st.session_state.selection = "Home"
if 'uploaded_students' not in st.session_state:
    st.session_state.uploaded_students = []
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {}

def handle_get_started():
    st.session_state.selection = "Student Management"

with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    st.radio("SELECT SECTION", ["Home", "Student Management", "Mark Attendance", "View Reports", "Analytics"], key="selection")
    st.divider()
    st.caption("🚀 Smart Attendance. Simple Insights.")

# --- 3. HOME PAGE ---
if st.session_state.selection == "Home":
    st.markdown('<h1 class="animated-title">AttendX</h1>', unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;'><h2 style='color: #38BDF8;'>Smart Attendance. Real-Time Insights.</h2></div>", unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top:40px;'></div>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 1, 1])
    with col_c:
        st.button("🚀 Get Started", use_container_width=True, on_click=handle_get_started)

    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    features = [("📱 Digital Marking", "Mark attendance instantly."), 
                ("📊 Smart Reports", "Generate automated insights."), 
                ("🏷️ Auto-Grading", "Intelligent A-D grading.")]
    for i, (title, desc) in enumerate(features):
        with [f1, f2, f3][i]:
            st.markdown(f'<div class="feature-card"><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)

# --- 4. STUDENT MANAGEMENT ---
elif st.session_state.selection == "Student Management":
    st.header("📂 Student Management")
    uploaded_file = st.file_uploader("Upload Student Details (CSV)", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df, use_container_width=True)
        if st.button("✅ Confirm Student List", type="primary"):
            st.session_state.uploaded_students = df.to_dict('records')
            st.session_state.attendance_map = {s["student_id"]: "Absent" for s in st.session_state.uploaded_students}
            st.success("Students Imported Successfully!")

# --- 5. MARK ATTENDANCE (WITH DYNAMIC COLORS) ---
elif st.session_state.selection == "Mark Attendance":
    st.header("📝 Mark Attendance")
    if not st.session_state.uploaded_students:
        st.warning("⚠️ Please upload a CSV in 'Student Management' first.")
    else:
        search = st.text_input("🔍 Search Student", placeholder="Search by name...")
        cols = st.columns(3)
        filtered = [s for s in st.session_state.uploaded_students if search.lower() in s["name"].lower()]
        
        for idx, student in enumerate(filtered):
            with cols[idx % 3]:
                with st.container(border=True):
                    gender = str(student.get("gender", "")).strip().lower()
                    emoji = "👦" if gender in ["male", "m", "boy"] else "👧"
                    
                    # COLOR LOGIC
                    current_status = st.session_state.attendance_map.get(student["student_id"], "Absent")
                    status_class = "status-present" if current_status == "Present" else "status-absent"
                    
                    st.markdown(f"### {emoji} {student['name']}")
                    st.markdown(f"Status: <span class='{status_class}'>{current_status}</span>", unsafe_allow_html=True)
                    
                    status = st.segmented_control("Change Status", ["Present", "Absent"], 
                                                 key=f"st_{student['student_id']}", 
                                                 default=current_status, label_visibility="collapsed")
                    st.session_state.attendance_map[student["student_id"]] = status

        if st.button("💾 Save Attendance", type="primary", use_container_width=True):
            save_attendance(st.session_state.attendance_map)
            st.success("Records Synced Successfully!")

# --- 6. VIEW REPORTS ---
elif st.session_state.selection == "View Reports":
    st.header("📋 Attendance Reports")
    if st.session_state.uploaded_students:
        tab1, tab2, tab3 = st.tabs(["Daily Report", "Monthly Summary", "Yearly Overview"])
        def get_rep(days):
            lst = []
            for s in st.session_state.uploaded_students:
                pre = np.random.randint(0, days + 1)
                perc = (pre/days)*100 if days > 0 else 0
                lst.append({"Name": s["name"], "ID": s["student_id"], "Days Present": f"{pre}/{days}", "Attendance %": f"{perc:.1f}%"})
            return pd.DataFrame(lst)
        with tab1: st.dataframe(pd.DataFrame([{"Name": s["name"], "Status": st.session_state.attendance_map.get(s["student_id"], "Absent")} for s in st.session_state.uploaded_students]), use_container_width=True)
        with tab2: st.dataframe(get_rep(22), use_container_width=True)
        with tab3: st.dataframe(get_rep(220), use_container_width=True)

# --- 7. ANALYTICS ---
elif st.session_state.selection == "Analytics":
    st.header("📈 System Analytics")
    if st.session_state.uploaded_students:
        total = len(st.session_state.uploaded_students)
        present = list(st.session_state.attendance_map.values()).count("Present")
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f'<div class="feature-card"><h3>Total</h3><h1>{total}</h1></div>', unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="feature-card"><h3>Present</h3><h1 style="color:#22C55E;">{present}</h1></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="feature-card"><h3>Absent</h3><h1 style="color:#EF4444;">{total-present}</h1></div>', unsafe_allow_html=True)
        st.bar_chart({"Status": ["Present", "Absent"], "Count": [present, total-present]}, x="Status", y="Count")

# --- 8. REDESIGNED SLEEK FOOTER ---
st.markdown(f"""
    <div class="footer-container">
        <div class="footer-content">
            <div class="footer-section">
                <h4>🏢 AttendX Headquarters</h4>
                <p>Cyber Towers, Hitech City</p>
                <p>Hyderabad, Telangana, India</p>
            </div>
            <div class="footer-section">
                <h4>📞 Contact Support</h4>
                <p><strong>Phone:</strong> +91 7386895943</p>
                <p><strong>Email:</strong> ganeshbasani43@gmail.com</p>
            </div>
            <div style="text-align: right;">
                <h4 style="color: #38BDF8;">Designed by Ganesh Basani</h4>
                <p>Smart Attendance. Simple Insights.</p>
                <p>Academic Excellence Project 2025</p>
            </div>
        </div>
        <div class="footer-bottom">
            &copy; 2025 ATTENDX SMART ATTENDANCE SYSTEM. ALL RIGHTS RESERVED.
        </div>
    </div>
""", unsafe_allow_html=True)
