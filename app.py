import streamlit as st
from datetime import datetime
from attendance import load_students, save_attendance

# 1. Page Config with your "Brand" Name
st.set_page_config(page_title="EduTrack Pro", page_icon="🎓", layout="wide")

# 2. Personalized CSS
st.markdown("""
    <style>
    /* Gradient Background for Sidebar */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(#2e3b4e, #1a2433);
        color: white;
    }
    /* Custom Card Styling */
    .st-emotion-cache-12w0qpk { 
        border-radius: 20px; 
        border: 1px solid #e0e0e0;
        transition: transform 0.2s ease;
    }
    .st-emotion-cache-12w0qpk:hover {
        transform: translateY(-5px);
        border: 1px solid #4b6cb7;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Sidebar Personalization
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: white;'>🎓 EduTrack</h1>", unsafe_allow_html=True)
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429153.png", width=100) # Replace with local logo path
    st.markdown("---")
    st.write(f"📅 **Date:** {datetime.now().strftime('%d %B, %Y')}")
    
    # User Personalization
    user_name = st.text_input("Instructor Name", "Professor Smith")
    st.success(f"Signed in as: {user_name}")

# 4. Dynamic Greeting
hour = datetime.now().hour
greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 18 else "Good Evening"
st.title(f"{greeting}, {user_name}! 👋")
st.caption("Here is your attendance overview for today's session.")

# 5. Data & State
students = load_students()
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {s["student_id"]: "Absent" for s in students}

# 6. Analytics Section
p_count = list(st.session_state.attendance_map.values()).count("Present")
total = len(students)

c1, c2, c3 = st.columns(3)
c1.metric("Students", total)
c2.metric("Checked In", p_count)
c3.progress(p_count/total if total > 0 else 0, text=f"{int((p_count/total)*100)}% Capacity")

st.divider()

# 7. Search & Filter
search = st.text_input("🔍 Search Student List", placeholder="Type a name...", label_visibility="collapsed")

# 8. Personalized Student Cards
filtered = [s for s in students if search.lower() in s["name"].lower()]

if not filtered:
    st.warning("No students found matching that name.")
else:
    cols = st.columns(4) # 4 columns for a more dense, app-like look
    for idx, student in enumerate(filtered):
        with cols[idx % 4]:
            with st.container(border=True):
                # Using a placeholder image if no photo exists
                st.image("https://www.w3schools.com/howto/img_avatar.png", width=70) 
                st.markdown(f"**{student['name']}**")
                st.caption(f"ID: {student['student_id']}")
                
                status = st.segmented_control(
                    "Status",
                    options=["Present", "Absent", "Late"],
                    key=f"st_{student['student_id']}",
                    default=st.session_state.attendance_map.get(student["student_id"], "Absent"),
                    label_visibility="collapsed"
                )
                st.session_state.attendance_map[student["student_id"]] = status

# 9. Save Button with Personal Touch
if st.button("🏁 Finish Session & Sync Records", type="primary", use_container_width=True):
    save_attendance(st.session_state.attendance_map)
    st.balloons()
    st.toast(f"Data synced for {p_count} students!", icon="🚀")
