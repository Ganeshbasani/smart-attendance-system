import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & CONFIG ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

# Custom CSS for AttendX Branding
st.markdown("""
    <style>
    .brand-title { color: #1E88E5; font-size: 42px; font-weight: 800; margin-bottom: 0px; }
    .brand-tagline { color: #546E7A; font-size: 18px; margin-bottom: 30px; }
    .feature-card { 
        background-color: white; padding: 20px; border-radius: 15px; 
        border-top: 5px solid #1E88E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color: #1E88E5;'>AttendX</h2>", unsafe_allow_html=True)
    page = st.radio("Navigation", ["Home", "Mark Attendance", "View Reports", "Analytics"], label_visibility="collapsed")
    st.divider()
    st.caption("Developed by: Your Name")
    st.caption("Academic Project 2024")

students = load_students()

# --- 3. LANDING PAGE (HOME) ---
if page == "Home":
    st.markdown('<p class="brand-title">AttendX</p>', unsafe_allow_html=True)
    st.markdown('<p class="brand-tagline">Smart Attendance. Simple Insights.</p>', unsafe_allow_html=True)
    
    st.subheader("System Features")
    f1, f2, f3 = st.columns(3)
    features = [
        ("📱 Digital Marking", "Mark attendance instantly with a clean mobile-friendly UI."),
        ("📊 Smart Reports", "Generate weekly, monthly, and yearly insights automatically."),
        ("🏷️ Auto-Grading", "System calculates grades (A-D) based on attendance %.")
    ]
    for i, (title, desc) in enumerate(features):
        with [f1, f2, f3][i]:
            st.markdown(f"""<div class="feature-card"><h3>{title}</h3><p>{desc}</p></div>""", unsafe_allow_html=True)

# --- 4. MARK ATTENDANCE ---
elif page == "Mark Attendance":
    st.header("📝 Mark Attendance")
    st.info(f"📅 **Date:** {datetime.now().strftime('%A, %d %B %Y')}")
    
    attendance_data = {}
    
    # Search Bar
    search = st.text_input("🔍 Find Student", placeholder="Search by name...")
    
    # Table Header
    h1, h2, h3 = st.columns([1, 2, 2])
    h1.write("**ID**")
    h2.write("**Student Name**")
    h3.write("**Status**")
    
    for s in students:
        if search.lower() in s["name"].lower():
            c1, c2, c3 = st.columns([1, 2, 2])
            c1.write(f"`{s['student_id']}`")
            c2.write(f"**{s['name']}**")
            status = c3.segmented_control(
                "Status", ["Present", "Absent"], 
                key=s["student_id"], default="Absent", label_visibility="collapsed"
            )
            attendance_data[s["student_id"]] = status
            
    if st.button("💾 Save Attendance", type="primary"):
        save_attendance(attendance_data)
        st.success("Attendance saved successfully!")
        st.balloons()

# --- 5. REPORTS & GRADING ---
elif page == "View Reports":
    st.header("📋 Attendance Reports")
    
    # Mock Data Logic for Demo
    data = []
    for s in students:
        perc = np.random.randint(50, 100)
        # Grading Logic
        if perc >= 90: grade, color = "A", "green"
        elif perc >= 80: grade, color = "B", "blue"
        elif perc >= 70: grade, color = "C", "orange"
        else: grade, color = "D", "red"
        
        data.append({"Name": s["name"], "Attendance %": perc, "Grade": grade})
    
    df = pd.DataFrame(data)
    st.table(df)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Report (CSV)", data=csv, file_name="attendance_report.csv", mime="text/csv")

# --- 6. ANALYTICS & VISUALIZATION ---
elif page == "Analytics":
    st.header("📈 Attendance Insights")
    
    # Visualization
    chart_data = pd.DataFrame({
        "Student": [s["name"] for s in students],
        "Attendance %": [np.random.randint(60, 100) for _ in students]
    })
    
    st.bar_chart(chart_data, x="Student", y="Attendance %", color="#1E88E5")
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("### Grade Distribution")
        # Logic for a simple pie-style summary could go here
    with c2:
        st.write("### Monthly Trend")
        st.line_chart(np.random.randn(10, 1))

# --- 7. FOOTER ---
st.markdown("---")
st.caption("AttendX – Smart Attendance System | Developed for Academic Excellence")
