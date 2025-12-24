import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import load_students, save_attendance

# --- 1. APP IDENTITY & CONFIG ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

# Updated Custom CSS for visibility and branding
st.markdown("""
    <style>
    /* Ultra-large Title */
    .brand-title { 
        color: #1E88E5; 
        font-size: 72px; /* Increased size */
        font-weight: 900; 
        margin-bottom: -10px;
        line-height: 1;
    }
    .brand-tagline { 
        color: #546E7A; 
        font-size: 22px; 
        margin-bottom: 40px; 
        font-weight: 400;
    }
    /* Fixed Card Visibility */
    .feature-card { 
        background-color: #ffffff; 
        padding: 25px; 
        border-radius: 15px; 
        border-top: 6px solid #1E88E5; 
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        min-height: 200px;
    }
    /* Ensuring text inside cards is dark and readable */
    .feature-card h3 { color: #1a1a1a !important; margin-bottom: 10px; }
    .feature-card p { color: #444444 !important; font-size: 16px; line-height: 1.4; }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAVIGATION & PERSONALIZED SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #1E88E5; font-size: 40px;'>AttendX</h1>", unsafe_allow_html=True)
    page = st.radio("Navigation", ["Home", "Mark Attendance", "View Reports", "Analytics"], label_visibility="collapsed")
    
    # Custom Sidebar Footer
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🛠️ Developer Info")
    st.info("**Designed by:** Ganesh Basani")
    st.caption("📅 **Year:** 2025")
    st.caption("🚀 Version 1.0.4")

students = load_students()

# --- 3. LANDING PAGE (HOME) ---
if page == "Home":
    # Larger Title as requested
    st.markdown('<h1 class="brand-title">AttendX</h1>', unsafe_allow_html=True)
    st.markdown('<p class="brand-tagline">Smart Attendance. Simple Insights.</p>', unsafe_allow_html=True)
    
    st.markdown("### 🚀 System Features")
    f1, f2, f3 = st.columns(3)
    
    # Feature Content
    features = [
        ("📱 Digital Marking", "Say goodbye to paper. Mark attendance instantly with our mobile-optimized digital interface."),
        ("📊 Smart Reports", "Automated weekly and monthly insights. Track trends and attendance drops at a glance."),
        ("🏷️ Auto-Grading", "Our intelligent system calculates academic grades (A-D) based on real-time attendance percentages.")
    ]
    
    col_list = [f1, f2, f3]
    for i, (title, desc) in enumerate(features):
        with col_list[i]:
            # Using HTML cards to force text color consistency
            st.markdown(f"""
                <div class="feature-card">
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>
            """, unsafe_allow_html=True)

# --- 4. MARK ATTENDANCE ---
elif page == "Mark Attendance":
    st.header("📝 Mark Attendance")
    st.info(f"📅 **Session Date:** {datetime.now().strftime('%A, %d %B %Y')}")
    
    # Search and Filter
    search = st.text_input("🔍 Search Student Database", placeholder="Start typing a name...")
    
    attendance_data = {}
    
    # Container for a clean table look
    with st.container(border=True):
        h1, h2, h3 = st.columns([1, 2, 2])
        h1.markdown("**ID**")
        h2.markdown("**Student Name**")
        h3.markdown("**Status**")
        st.divider()
        
        for s in students:
            if search.lower() in s["name"].lower():
                c1, c2, c3 = st.columns([1, 2, 2])
                c1.code(s['student_id'])
                c2.markdown(f"**{s['name']}**")
                status = c3.segmented_control(
                    "Status", ["Present", "Absent"], 
                    key=f"id_{s['student_id']}", 
                    default="Absent", 
                    label_visibility="collapsed"
                )
                attendance_data[s["student_id"]] = status

    if st.button("💾 Finalize & Save Attendance", type="primary", use_container_width=True):
        save_attendance(attendance_data)
        st.success(f"Successfully saved records for {len(attendance_data)} students!")
        st.balloons()

# --- 5. REPORTS & ANALYTICS (Placeholders for logic) ---
elif page == "View Reports":
    st.header("📋 Attendance Reports")
    st.write("Generating report data...")
    # Add your report generation logic here

elif page == "Analytics":
    st.header("📈 Deep Analytics")
    st.write("Visualizing attendance trends...")
    # Add your chart/graph logic here

# --- 6. FOOTER ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()
footer_col1, footer_col2 = st.columns([2, 1])
with footer_col1:
    st.caption("AttendX – Smart Attendance System | Academic Project 2025")
with footer_col2:
    st.markdown("<p style='text-align: right; font-size: 12px;'>Designed by Ganesh Basani</p>", unsafe_allow_html=True)
