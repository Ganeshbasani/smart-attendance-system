import streamlit as st
from attendance import load_students, save_attendance

# 1. Advanced Page Config
st.set_page_config(page_title="Smart Attendance Pro", layout="wide", initial_sidebar_state="expanded")

# 2. Enhanced CSS (The "Attractive" Layer)
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
    
    /* Custom Styling for the Student Cards */
    .student-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #4b6cb7;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Logic & Data Initialization
students = load_students()

# IMPORTANT: Initialize session state so data isn't lost during reruns
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {s["student_id"]: "Absent" for s in students}

# 4. Header Section
st.title("📘 Smart Attendance System")
t1, t2 = st.columns([2, 1])
with t1:
    search = st.text_input("🔍 Quick Search", placeholder="Enter student name...", label_visibility="collapsed")
with t2:
    # Quick Action to mark everyone present (Convenience feature)
    if st.button("✅ Mark All Present"):
        for s in students: st.session_state.attendance_map[s["student_id"]] = "Present"
        st.rerun()

# 5. Live Analytics Dashboard
present_count = list(st.session_state.attendance_map.values()).count("Present")
total = len(students)

m1, m2, m3 = st.columns(3)
m1.metric("Enrolled", total)
m2.metric("Checked In", present_count, delta=f"{present_count - total} remaining", delta_color="inverse")
m3.metric("Attendance %", f"{(present_count/total)*100:.0f}%")

st.divider()

# 6. Optimized Student Grid
filtered_students = [s for s in students if search.lower() in s["name"].lower()]
cols = st.columns(3)

for idx, student in enumerate(filtered_students):
    with cols[idx % 3]:
        # Using the new "border" container for a card effect
        with st.container(border=True):
            st.markdown(f"### {student['name']}")
            st.caption(f"🆔 {student['student_id']}")
            
            # Using segmented_control or pills for modern feel
            status = st.segmented_control(
                "Status",
                options=["Present", "Absent"],
                key=f"status_{student['student_id']}",
                default=st.session_state.attendance_map[student["student_id"]],
                label_visibility="collapsed"
            )
            # Update state immediately
            st.session_state.attendance_map[student["student_id"]] = status

# 7. Fixed Footer Action
st.sidebar.markdown("---")
st.sidebar.header("System Controls")
if st.sidebar.button("💾 Save to Database", use_container_width=True, type="primary"):
    save_attendance(st.session_state.attendance_map)
    st.sidebar.success("Records Locked!")
    st.toast("Attendance saved successfully!", icon="✅")
