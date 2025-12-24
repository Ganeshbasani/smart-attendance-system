import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & THEME CONFIG ---
# Using the specific hex codes from your specs
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

# Custom CSS for the "Soft Blue–Purple" Dark Theme
st.markdown(f"""
    <style>
    /* Background & Main Layout */
    .stApp {{
        background-color: #0B1120;
        color: #F9FAFB;
    }}
    
    /* Hero Title & Text */
    .hero-title {{
        color: #2563EB;
        font-size: 64px;
        font-weight: 900;
        margin-bottom: 0px;
    }}
    .hero-tagline {{
        color: #38BDF8;
        font-size: 24px;
        margin-bottom: 20px;
    }}
    
    /* Feature Cards */
    .feature-card {{
        background-color: #1F2937;
        padding: 25px;
        border-radius: 15px;
        border-left: 5px solid #F97316;
        min-height: 180px;
        margin-bottom: 20px;
    }}
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background-color: #0B1120;
        border-right: 1px solid #1F2937;
    }}
    
    /* Buttons */
    .stButton>button {{
        background-color: #2563EB !important;
        color: white !important;
        border-radius: 8px;
        border: none;
    }}
    
    /* Student Cards visibility fix */
    div[data-testid="stExpander"] {{
        background-color: #1F2937 !important;
        border: none !important;
    }}
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
students = load_students() # Ensure your attendance.py has 'gender' key (e.g., "Male" or "Female")
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {s["student_id"]: "Absent" for s in students}

# --- 4. HOME / HERO PAGE ---
if page == "Home":
    # Hero Section
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.markdown('<p class="hero-title">AttendX</p>', unsafe_allow_html=True)
        st.markdown('<p class="hero-tagline">Smart Attendance. Real-Time Insights.</p>', unsafe_allow_html=True)
        st.write("Replace paper registers with seamless digital marking and powerful analytics. AttendX provides a modern approach to managing classroom and office presence.")
        
        c1, c2 = st.columns(2)
        with c1: st.button("🚀 Get Started", use_container_width=True)
        with c2: st.button("📺 View Demo", use_container_width=True)
        
    with col2:
        # Illustration placeholder
        st.image("https://img.freepik.com/free-vector/gradient-ui-ux-background_23-2149051557.jpg", use_container_width=True)

    st.markdown("---")
    
    # Feature Cards Section
    st.subheader("Key Capabilities")
    f1, f2, f3 = st.columns(3)
    features = [
        ("📱 Digital Marking", "Mark attendance instantly via web or mobile interface."),
        ("📊 Smart Reports", "Generate automated insights with detailed export options."),
        ("🏷️ Auto-Grading", "Intelligent A-D grading based on participation levels.")
    ]
    for i, (title, desc) in enumerate(features):
        with [f1, f2, f3][i]:
            st.markdown(f"""<div class="feature-card"><h3>{title}</h3><p>{desc}</p></div>""", unsafe_allow_html=True)

# --- 5. ATTENDANCE MARKING (CORE LOGIC) ---
elif page == "Mark Attendance":
    st.header("📝 Mark Attendance")
    st.info(f"📅 Session Date: {datetime.now().strftime('%d %B, %Y')}")
    
    search = st.text_input("🔍 Search Student", placeholder="Search by name...", label_visibility="collapsed")
    
    # Student List with Gender Emojis
    cols = st.columns(3)
    filtered = [s for s in students if search.lower() in s["name"].lower()]
    
    for idx, student in enumerate(filtered):
        with cols[idx % 3]:
            with st.container(border=True):
                # Gender Emoji Logic
                # Assumes 'gender' exists in your load_students() data
                gender_icon = "👦" if student.get("gender") == "Male" else "👧"
                
                st.markdown(f"### {gender_icon} {student['name']}")
                st.caption(f"ID: {student['student_id']}")
                
                status = st.segmented_control(
                    "Status", ["Present", "Absent"],
                    key=f"st_{student['student_id']}",
                    default=st.session_state.attendance_map.get(student["student_id"], "Absent"),
                    label_visibility="collapsed"
                )
                st.session_state.attendance_map[student["student_id"]] = status

    if st.button("✅ Save & Sync Records", type="primary"):
        save_attendance(st.session_state.attendance_map)
        st.success("Database Updated!")
        st.balloons()

# --- 6. REPORTS SECTION ---
elif page == "View Reports":
    st.header("📋 Reports Vault")
    
    report_type = st.tabs(["📅 Weekly", "🗓️ Monthly", "📊 Yearly"])
    
    for tab in report_type:
        with tab:
            # Generate dummy reporting data
            data = pd.DataFrame({
                "Student Name": [s["name"] for s in students],
                "Classes Attended": [np.random.randint(5, 20) for _ in students],
                "Attendance %": [np.random.randint(60, 100) for _ in students]
            })
            st.dataframe(data, use_container_width=True)
            st.download_button("📥 Export CSV", data=data.to_csv().encode('utf-8'), file_name="attendx_report.csv")

# --- 7. FOOTER SECTION ---
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.divider()

f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    st.markdown("### 🏢 AttendX")
    st.caption("Smart Attendance. Simple Insights.")
    st.caption("© 2025 All Rights Reserved.")

with f_col2:
    st.markdown("### 📞 Contact Details")
    st.markdown("📧 ganeshbasani43@gmail.com")
    st.markdown("📱 +91 7386895943")

with f_col3:
    st.markdown("### 📍 Location")
    st.markdown("Cyber Towers, Hitech City")
    st.markdown("Hyderabad, Telangana, India")

st.markdown("<p style='text-align: center; color: #38BDF8;'>Designed by Ganesh Basani</p>", unsafe_allow_html=True)
