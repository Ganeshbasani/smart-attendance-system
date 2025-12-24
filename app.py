import streamlit as st
import pandas as pd
from datetime import datetime
from attendance import load_students, save_attendance

st.set_page_config(
    page_title="AttendX | Smart Attendance System",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.brand-title {
    color: #1E88E5;
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 0;
}
.brand-tagline {
    color: #546E7A;
    font-size: 18px;
    margin-bottom: 30px;
}
.feature-card {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 12px;
    border-left: 6px solid #1E88E5;
    box-shadow: 0 4px 8px rgba(0,0,0,0.05);
}
.section-title {
    font-size: 24px;
    font-weight: 700;
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)

def calculate_grade(attendance_percentage):
    if attendance_percentage >= 90:
        return "A"
    elif attendance_percentage >= 80:
        return "B"
    elif attendance_percentage >= 70:
        return "C"
    else:
        return "D"

with st.sidebar:
    st.markdown("<h2 style='color:#1E88E5;'>AttendX</h2>", unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        ["Home", "Mark Attendance", "Reports"],
        label_visibility="collapsed"
    )
    st.divider()
    st.caption("Developed by Basani Ganesh")
    st.caption("Academic Project")

students = load_students()

# ---------------- HOME ----------------
if page == "Home":
    st.markdown("<p class='brand-title'>AttendX</p>", unsafe_allow_html=True)
    st.markdown("<p class='brand-tagline'>Smart Attendance. Simple Insights.</p>", unsafe_allow_html=True)

    st.markdown("<p class='section-title'>Core Features</p>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='feature-card'><b>Digital Attendance</b><br>Mark attendance quickly and accurately.</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='feature-card'><b>Automated Reports</b><br>Generate weekly, monthly, and yearly summaries.</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='feature-card'><b>Attendance Grading</b><br>Automatic grading based on attendance percentage.</div>", unsafe_allow_html=True)

# ---------------- MARK ATTENDANCE ----------------
elif page == "Mark Attendance":
    st.markdown("<p class='section-title'>Mark Attendance</p>", unsafe_allow_html=True)
    st.info(f"Date: {datetime.now().strftime('%d %B %Y')}")

    attendance_data = {}
    search = st.text_input("Search student by name")

    h1, h2, h3 = st.columns([1, 3, 2])
    h1.write("ID")
    h2.write("Student Name")
    h3.write("Status")

    found = False
    for s in students:
        if search.lower() in s["name"].lower():
            found = True
            c1, c2, c3 = st.columns([1, 3, 2])
            c1.write(s["student_id"])
            c2.write(s["name"])
            attendance_data[s["student_id"]] = c3.radio(
                "Status",
                ["Present", "Absent"],
                key=s["student_id"],
                horizontal=True,
                label_visibility="collapsed"
            )

    if not found:
        st.warning("No students found for the given search.")

    if st.button("Save Attendance", type="primary"):
        save_attendance(attendance_data)
        st.success("Attendance saved successfully.")

# ---------------- REPORTS ----------------
elif page == "Reports":
    st.markdown("<p class='section-title'>Attendance Report</p>", unsafe_allow_html=True)

    report_data = []
    for s in students:
        total_classes = 30
        present_days = 22
        percentage = round((present_days / total_classes) * 100, 2)
        grade = calculate_grade(percentage)

        report_data.append({
            "Student Name": s["name"],
            "Total Classes": total_classes,
            "Present Days": present_days,
            "Attendance %": percentage,
            "Grade": grade
        })

    df = pd.DataFrame(report_data)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Report (CSV)",
        csv,
        "AttendX_Attendance_Report.csv",
        "text/csv"
    )

st.markdown("---")
st.caption("AttendX – Smart Attendance System | Academic Use")
