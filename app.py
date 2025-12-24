import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & THEME CONFIG ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: #0B1120; color: #F9FAFB; }}
    .hero-title {{ color: #2563EB; font-size: 64px; font-weight: 900; margin: 0; }}
    .hero-tagline {{ color: #38BDF8; font-size: 24px; margin-bottom: 20px; }}
    .feature-card {{ 
        background-color: #1F2937; padding: 25px; border-radius: 15px; 
        border-left: 5px solid #F97316; min-height: 180px; margin-bottom: 20px; 
    }}
    [data-testid="stSidebar"] {{ background-color: #0B1120; border-right: 1px solid #1F2937; }}
    /* Force text visibility in cards */
    .feature-card h3, .feature-card p {{ color: #F9FAFB !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAVIGATION ---
with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    page = st.radio("SELECT SECTION", ["Home", "Mark Attendance", "View Reports", "Analytics"], label_visibility="collapsed")
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### 👨‍💻 Developed By")
    st.markdown("**Ganesh Basani**")
    st.caption("Academic Project 2025")

# --- 3. DATA LOADING ---
students = load_students()
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {s["student_id"]: "Absent" for s in students}

# --- 4. HOME PAGE ---
if page == "Home":
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.markdown('<p class="hero-title">AttendX</p>', unsafe_allow_html=True)
        st.markdown('<p class="hero-tagline">Smart Attendance. Real-Time Insights.</p>', unsafe_allow_html=True)
        st.write("Replace paper registers with digital marking and powerful analytics.")
        c1, c2 = st.columns(2)
        with c1: st.button("🚀 Get Started", key="get_started_btn")
        with c2: st.button("📺 View Demo", key="view_demo_btn")
    with col2:
        st.image("https://img.freepik.com/free-vector/gradient-ui-ux-background_23-2149051557.jpg")

    st.divider()
    f1, f2, f3 = st.columns(3)
    features = [("📱 Digital Marking", "Mark attendance instantly."), 
                ("📊 Smart Reports", "Generate automated insights."), 
                ("🏷️ Auto-Grading", "Intelligent A-D grading.")]
    for i, (title, desc) in enumerate(features):
        with [f1, f2, f3][i]:
            st.markdown(f'<div class="feature-card"><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)

# --- 5. MARK ATTENDANCE (FIXED EMOJIS) ---
elif page == "Mark Attendance":
    st.header("📝 Mark Attendance")
    search = st.text_input("🔍 Search Student", placeholder="Search by name...", label_visibility="collapsed")
    
    cols = st.columns(3)
    filtered = [s for s in students if search.lower() in s["name"].lower()]
    
    for idx, student in enumerate(filtered):
        with cols[idx % 3]:
            with st.container(border=True):
                # FIXED GENDER LOGIC: Handles "Male", "male", "M" and missing keys
                gender = str(student.get("gender", "")).strip().lower()
                gender_icon = "👦" if gender in ["male", "m", "boy"] else "👧"
                
                st.markdown(f"### {gender_icon} {student['name']}")
                st.caption(f"ID: {student['student_id']}")
                
                status = st.segmented_control(
                    "Status", ["Present", "Absent"],
                    key=f"status_{student['student_id']}",
                    default=st.session_state.attendance_map.get(student["student_id"], "Absent"),
                    label_visibility="collapsed"
                )
                st.session_state.attendance_map[student["student_id"]] = status

    if st.button("✅ Save & Sync Records", type="primary"):
        save_attendance(st.session_state.attendance_map)
        st.success("Database Updated!")
        st.balloons()

# --- 6. REPORTS SECTION (FIXED DUPLICATE ID) ---
elif page == "View Reports":
    st.header("📋 Reports Vault")
    tab_names = ["Weekly", "Monthly", "Yearly"]
    tabs = st.tabs([f"📅 {t}" for t in tab_names])
    
    for i, tab in enumerate(tabs):
        with tab:
            data = pd.DataFrame({
                "Student Name": [s["name"] for s in students],
                "Attendance %": [np.random.randint(60, 100) for _ in students]
            })
            st.dataframe(data, use_container_width=True)
            
            # FIXED: Added unique 'key' to prevent DuplicateElementId error
            st.download_button(
                label=f"📥 Export {tab_names[i]} CSV", 
                data=data.to_csv().encode('utf-8'), 
                file_name=f"attendx_{tab_names[i].lower()}_report.csv",
                key=f"download_btn_{tab_names[i]}" 
            )

# --- 7. FOOTER SECTION ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()
f_col1, f_col2, f_col3 = st.columns(3)
with f_col1:
    st.markdown("### 🏢 AttendX")
    st.caption("© 2025 All Rights Reserved.")
with f_col2:
    st.markdown("### 📞 Contact Details")
    st.markdown("📧 ganeshbasani43@gmail.com\n\n📱 +91 7386895943")
with f_col3:
    st.markdown("### 📍 Location")
    st.markdown("Cyber Towers, Hitech City\n\nHyderabad, Telangana")

st.markdown("<p style='text-align: center; color: #38BDF8;'>Designed by Ganesh Basani</p>", unsafe_allow_html=True)
