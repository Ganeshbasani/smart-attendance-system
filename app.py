import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import save_attendance

# --- 1. APP IDENTITY & THEME CONFIG (STRICTLY PRESERVED) ---
st.set_page_config(page_title="AttendX | Smart Attendance", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    @keyframes titleGlow {
        0% { opacity: 0; transform: scale(0.9); text-shadow: 0 0 0px #2563EB; }
        50% { opacity: 1; transform: scale(1.05); text-shadow: 0 0 20px #2563EB; }
        100% { opacity: 1; transform: scale(1); text-shadow: 0 0 10px #2563EB; }
    }
    .stApp {
        background: linear-gradient(rgba(11, 17, 32, 0.85), rgba(11, 17, 32, 0.85)), 
                    url('https://www.transparenttextures.com/patterns/carbon-fibre.png'),
                    url('https://img.icons8.com/ios/452/fingerprint.png'); 
        background-repeat: repeat, repeat, no-repeat;
        background-position: center; background-attachment: fixed;
        background-color: #0B1120; color: #F9FAFB;
    }
    .animated-title {
        color: #2563EB; font-size: 100px; font-weight: 900; text-align: center;
        animation: titleGlow 2.5s ease-out; margin-bottom: 0px;
    }
    .status-present { color: #22C55E !important; font-weight: bold; }
    .status-absent { color: #EF4444 !important; font-weight: bold; }
    .feature-card {
        background-color: rgba(31, 41, 55, 0.7); padding: 25px; border-radius: 15px;
        border-bottom: 4px solid #2563EB; text-align: center; margin-bottom: 30px;
    }
    .left-bottom-credit {
        position: fixed; bottom: 20px; left: 20px; font-size: 13px; color: #94A3B8;
        z-index: 100; background: rgba(15, 23, 42, 0.9); padding: 10px 15px;
        border-radius: 8px; border-left: 4px solid #2563EB; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .footer-container {
        margin-top: 150px; padding: 60px 0 30px 0;
        background: rgba(15, 23, 42, 0.8); border-top: 1px solid rgba(37, 99, 235, 0.2);
        backdrop-filter: blur(10px);
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""<div class="left-bottom-credit">Designed by: Ganesh Basani<br>📅 Year: 2025</div>""", unsafe_allow_html=True)

# --- 2. STATE INITIALIZATION ---
# We initialize values only if they don't exist
if 'selection' not in st.session_state:
    st.session_state['selection'] = "Home"
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'uploaded_students' not in st.session_state:
    st.session_state.uploaded_students = []
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {}

# --- 3. TOP RIGHT AUTH ICONS ---
c_space, c_login, c_reg = st.columns([7, 1.5, 1.5])

with c_login:
    if not st.session_state.authenticated:
        if st.button("👤 Login", use_container_width=True): 
            st.session_state.selection = "Login"
            st.rerun()
    else:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.selection = "Home"
            st.rerun()

with c_reg:
    if not st.session_state.authenticated:
        if st.button("📝 Register", use_container_width=True): 
            st.session_state.selection = "Register"
            st.rerun()

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    
    # Define main pages
    main_pages = ["Home", "Student Management", "Mark Attendance", "View Reports", "Analytics"]
    
    # Technical fix: Ensure the radio widget can handle "Login" or "Register" 
    # even though they aren't in the permanent list
    current_options = main_pages
    if st.session_state.selection not in main_pages:
        current_options = main_pages + [st.session_state.selection]
    
    # Using index instead of key="selection" prevents the StreamlitAPIException
    selected_page = st.radio(
        "SELECT SECTION", 
        current_options, 
        index=current_options.index(st.session_state.selection)
    )
    
    # Manual update only if changed
    if selected_page != st.session_state.selection:
        st.session_state.selection = selected_page
        st.rerun()

    st.divider()
    st.caption(f"**Designed by:** Ganesh Basani")

# --- 5. PAGE CONTENT ---

# HOME PAGE
if st.session_state.selection == "Home":
    st.markdown('<h1 class="animated-title">AttendX</h1>', unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;'><h2 style='color: #38BDF8;'>Smart Attendance. Real-Time Insights.</h2></div>", unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top:40px;'></div>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 1, 1])
    with col_c:
        # Redirect logic
        if st.button("🚀 Get Started", use_container_width=True):
            st.session_state.selection = "Student Management" if st.session_state.authenticated else "Login"
            st.rerun()
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    features = [("📱 Digital Marking", "Mark attendance instantly."), 
                ("📊 Smart Reports", "Generate automated insights."), 
                ("🏷️ Auto-Grading", "Intelligent A-D grading.")]
    for i, (title, desc) in enumerate(features):
        with [f1, f2, f3][i]:
            st.markdown(f'<div class="feature-card"><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)

# LOGIN PAGE
elif st.session_state.selection == "Login":
    st.header("👤 Teacher Login")
    with st.container(border=True):
        st.text_input("user id :", key="login_user")
        st.text_input("password :", type="password", key="login_pass")
        if st.button("Submit Login", type="primary"):
            st.session_state.authenticated = True
            st.session_state.selection = "Home"
            st.success("Login Successful!")
            st.rerun()

# REGISTER PAGE
elif st.session_state.selection == "Register":
    st.header("📝 Create Teacher Account")
    with st.container(border=True):
        st.text_input("first name", key="reg_first")
        st.text_input("last name", key="reg_last")
        st.text_input("e-mail id :", key="reg_email")
        st.text_input("password:", type="password", key="reg_pass")
        if st.button("Submit Registration", type="primary"):
            st.success("Registration Successful! Please login.")
            st.session_state.selection = "Login"
            st.rerun()

# STUDENT MANAGEMENT
elif st.session_state.selection == "Student Management":
    st.header("📂 Student Management")
    if not st.session_state.authenticated:
        st.warning("🔒 Please Login to access Student Management.")
    else:
        uploaded_file = st.file_uploader("Upload Student Details (CSV)", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df, use_container_width=True)
            if st.button("✅ Confirm Student List"):
                st.session_state.uploaded_students = df.to_dict('records')
                st.session_state.attendance_map = {s["student_id"]: "Absent" for s in st.session_state.uploaded_students}
                st.success("Students Uploaded Successfully!")

# MARK ATTENDANCE
elif st.session_state.selection == "Mark Attendance":
    st.header("📝 Mark Attendance")
    if not st.session_state.authenticated:
        st.warning("🔒 Please Login to mark attendance.")
    elif not st.session_state.uploaded_students:
        st.warning("⚠️ Please upload a CSV in 'Student Management' first.")
    else:
        search = st.text_input("🔍 Search Student", placeholder="Search by name...")
        cols = st.columns(3)
        filtered = [s for s in st.session_state.uploaded_students if search.lower() in s["name"].lower()]
        for idx, student in enumerate(filtered):
            with cols[idx % 3]:
                with st.container(border=True):
                    gender = str(student.get("gender", "")).strip().lower()
                    emoji = "👦" if gender in ["male", "m", "boy"] else "👧"
                    current_status = st.session_state.attendance_map.get(student["student_id"], "Absent")
                    color = "status-present" if current_status == "Present" else "status-absent"
                    st.markdown(f"### {emoji} {student['name']}")
                    st.markdown(f"Status: <span class='{color}'>{current_status}</span>", unsafe_allow_html=True)
                    st.session_state.attendance_map[student["student_id"]] = st.segmented_control("Change Status", ["Present", "Absent"], key=f"btn_{student['student_id']}", default=current_status, label_visibility="collapsed")
        
        if st.button("💾 Save Attendance", type="primary", use_container_width=True):
            save_attendance(st.session_state.attendance_map)
            st.success("Attendance Saved!")

# VIEW REPORTS
elif st.session_state.selection == "View Reports":
    st.header("📋 Attendance Reports")
    if not st.session_state.uploaded_students:
        st.warning("⚠️ No data available. Upload students first.")
    else:
        tab1, tab2, tab3 = st.tabs(["Daily Report", "Monthly Summary", "Yearly Overview"])
        def get_rep(days):
            lst = []
            for s in st.session_state.uploaded_students:
                pre = np.random.randint(0, days + 1)
                perc = (pre/days)*100 if days > 0 else 0
                lst.append({"Name": s["name"], "ID": s["student_id"], "Days Present": f"{pre}/{days}", "Attendance %": f"{perc:.1f}%"})
            return pd.DataFrame(lst)
        with tab1: st.dataframe(pd.DataFrame([{"Name": s["name"], "Status": st.session_state.attendance_map.get(s["student_id"], "Absent")} for s in st.session_state.uploaded_students]), use_container_width=True)
        with tab2: st.dataframe(get_rep(22), use_container_width=True)
        with tab3: st.dataframe(get_rep(220), use_container_width=True)

# ANALYTICS
elif st.session_state.selection == "Analytics":
    st.header("📈 System Analytics")
    if not st.session_state.uploaded_students:
        st.warning("⚠️ No data available.")
    else:
        total = len(st.session_state.uploaded_students)
        present = list(st.session_state.attendance_map.values()).count("Present")
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f'<div class="feature-card"><h3>Total</h3><h1>{total}</h1></div>', unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="feature-card"><h3>Present</h3><h1 style="color:#22C55E;">{present}</h1></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="feature-card"><h3>Absent</h3><h1 style="color:#EF4444;">{total-present}</h1></div>', unsafe_allow_html=True)
        st.bar_chart({"Status": ["Present", "Absent"], "Count": [present, total-present]}, x="Status", y="Count")

# --- 6. FOOTER SECTION (STRICTLY PRESERVED) ---
st.markdown(f"""
    <div class="footer-container">
        <div class="footer-content">
            <div class="footer-section">
                <h4>🏢 AttendX Headquarters</h4>
                <p>Cyber Towers, Hitech City, Hyderabad</p>
            </div>
            <div class="footer-section">
                <h4>📞 Contact Support</h4>
                <p>Phone: +91 7386895943</p>
                <p>Email: ganeshbasani43@gmail.com</p>
            </div>
            <div style="text-align: right;">
                <h4 style="color: #38BDF8;">Designed by Ganesh Basani</h4>
                <p>© 2025 All Rights Reserved.</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)
