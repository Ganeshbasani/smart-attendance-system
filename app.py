import streamlit as st
from attendance import load_students, save_attendance

# 1. Page Configuration
st.set_page_config(page_title="Smart Attendence", page_icon="📘", layout="wide")

# 2. Custom CSS for High-Tech Look
st.markdown("""
    <style>
    /* Main background and font */
    .stApp { background-color: #f8f9fa; }
    
    /* Customizing the 'Card' look */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Make the Save button pop */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Header & Search
st.title("📘 Smart Attendance System")
search_query = st.text_input("🔍 Search student by name or ID...", placeholder="Type to filter...")

# 4. State Management
students = load_students()
if "attendance_data" not in st.session_state:
    st.session_state.attendance_data = {s["student_id"]: "Absent" for s in students}

# 5. Real-time Metrics Dashboard
total_students = len(students)
present_count = list(st.session_state.attendance_data.values()).count("Present")
absent_count = total_students - present_count

m1, m2, m3 = st.columns(3)
m1.metric("Total Enrolled", total_students)
m2.metric("Present Today", present_count, delta=f"{present_count} marked", delta_color="normal")
m3.metric("Attendance Rate", f"{(present_count/total_students)*100:.1f}%")

st.divider()

# 6. Student Grid Layout
st.subheader("Student Directory")
filtered_students = [s for s in students if search_query.lower() in s["name"].lower()]

# Display in a 3-column grid
cols = st.columns(3)
for i, student in enumerate(filtered_students):
    with cols[i % 3]:
        with st.container(border=True):
            # Student Info
            c1, c2 = st.columns([1, 3])
            with c1:
                st.write("👤") # Placeholder for Avatar
            with c2:
                st.markdown(f"**{student['name']}**")
                st.caption(f"ID: {student['student_id']}")
            
            # Action: Toggle Status
            # Using pills for a sleek button-toggle feel
            status = st.pills(
                label="Attendance Status",
                options=["Present", "Absent"],
                key=f"pill_{student['student_id']}",
                label_visibility="collapsed",
                default=st.session_state.attendance_data[student["student_id"]]
            )
            st.session_state.attendance_data[student["student_id"]] = status

# 7. Action Bar
st.sidebar.header("Actions")
if st.sidebar.button("🚀 Finalize & Save"):
    save_attendance(st.session_state.attendance_data)
    st.sidebar.success("Database Updated!")
    st.balloons()
