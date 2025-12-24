import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & CONFIG ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

# Advanced Personalized CSS
st.markdown("""
    <style>
    /* Main Title and Branding */
    .brand-title { 
        color: #1E88E5; 
        font-size: 72px; 
        font-weight: 900; 
        margin-bottom: -10px;
        line-height: 1;
    }
    .brand-tagline { 
        color: #546E7A; 
        font-size: 20px; 
        margin-bottom: 30px; 
    }
    
    /* Feature & Student Card Styling */
    .st-emotion-cache-12w0qpk { 
        background-color: #ffffff !important;
        border-radius: 15px !important; 
        padding: 20px !important;
        border: 1px solid #e0e0e0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    }
    
    /* Fix for text visibility in cards */
    .st-emotion-cache-12w0qpk p, .st-emotion-cache-12w0qpk h3, .st-emotion-cache-12w0qpk span {
        color: #1a1a1a !important;
    }

    /* Gradient Background for Sidebar */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(#1E88E5, #1565C0);
        color: white;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>AttendX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Smart Attendance. Simple Insights.</p>", unsafe_allow_html=True)
    st.divider()
    
    page = st.radio("MAIN NAVIGATION", ["Home", "Mark Attendance", "View Reports", "Analytics"], label_visibility="collapsed")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🛠️ Developer Info")
    st.markdown("**Designed by:** Ganesh Basani")
    st.caption("📅 **Year:** 2025")
    st.caption("Academic Project")

# --- 3. DATA & LOGIC INITIALIZATION ---
students = load_students()
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {s["student_id"]: "Absent" for s in students}

# --- 4. NAVIGATION LOGIC ---

# PAGE: HOME / LANDING
if page == "Home":
    st.markdown('<p class="brand-title">AttendX</p>', unsafe_allow_html=True)
    st.markdown('<p class="brand-tagline">Smart Attendance. Simple Insights.</p>', unsafe_allow_html=True)
    
    st.subheader("🚀 System Features")
    f1, f2, f3 = st.columns(3)
    
    with f1:
        with st.container(border=True):
            st.markdown("### 📱 Digital Marking")
            st.write("Mark attendance instantly with a clean, mobile-optimized digital interface.")
    with f2:
        with st.container(border=True):
            st.markdown("### 📊 Smart Reports")
            st.write("Generate weekly, monthly, and yearly insights automatically with one click.")
    with f3:
        with st.container(border=True):
            st.markdown("### 🏷️ Auto-Grading")
            st.write("Intelligent grading system (A-D) based on real-time attendance percentage.")

# PAGE: MARK ATTENDANCE
elif page == "Mark Attendance":
    st.header("📝 Mark Attendance")
    st.info(f"📅 **Session Date:** {datetime.now().strftime('%A, %d %B %Y')}")
    
    # Search Bar
    search = st.text_input("🔍 Search Student Database", placeholder="Type a name...", label_visibility="collapsed")
    filtered = [s for s in students if search.lower() in s["name"].lower()]

    # Student Grid
    cols = st.columns(4)
    for idx, student in enumerate(filtered):
        with cols[idx % 4]:
            with st.container(border=True):
                st.image("https://www.w3schools.com/howto/img_avatar.png", width=60) 
                st.markdown(f"**{student['name']}**")
                st.caption(f"ID: {student['student_id']}")
                
                status = st.segmented_control(
                    "Status",
                    options=["Present", "Absent"],
                    key=f"id_{student['student_id']}",
                    default=st.session_state.attendance_map.get(student["student_id"], "Absent"),
                    label_visibility="collapsed"
                )
                st.session_state.attendance_map[student["student_id"]] = status

    if st.button("🏁 Finish Session & Sync Records", type="primary", use_container_width=True):
        save_attendance(st.session_state.attendance_map)
        st.balloons()
        st.toast("Attendance data synced successfully!", icon="🚀")

# PAGE: REPORTS
elif page == "View Reports":
    st.header("📋 Attendance Reports")
    
    # Example Grading Calculation
    report_list = []
    for s in students:
        # Mocking attendance % for demonstration
        perc = np.random.randint(60, 100)
        if perc >= 90: grade = "A"
        elif perc >= 80: grade = "B"
        elif perc >= 70: grade = "C"
        else: grade = "D"
        
        report_list.append({
            "Name": s["name"],
            "Attendance %": perc,
            "Grade": grade
        })
    
    df = pd.DataFrame(report_list)
    st.dataframe(df, use_container_width=True)
    
    st.download_button("📥 Download Report (CSV)", data=df.to_csv().encode('utf-8'), file_name="attendance.csv")

# PAGE: ANALYTICS
elif page == "Analytics":
    st.header("📈 Analytics & Visualization")
    chart_data = pd.DataFrame({
        "Student": [s["name"] for s in students],
        "Attendance %": [np.random.randint(50, 100) for _ in students]
    })
    st.bar_chart(chart_data, x="Student", y="Attendance %", color="#1E88E5")

# --- 5. FOOTER ---
st.divider()
st.caption(f"AttendX – Smart Attendance System | Designed by Ganesh Basani | © 2025")
