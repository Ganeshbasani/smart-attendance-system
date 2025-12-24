import streamlit as st
from attendance import load_students, save_attendance

st.title("📘 Smart Attendance System")

students = load_students()
attendance = {}

st.subheader("Mark Attendance")

for student in students:
    status = st.radio(
        student["name"],
        ["Present", "Absent"],
        horizontal=True,
        key=student["student_id"]
    )
    attendance[student["student_id"]] = status

if st.button("Save Attendance"):
    save_attendance(attendance)
    st.success("Attendance saved successfully")

