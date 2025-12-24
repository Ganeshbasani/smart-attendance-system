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
if 'selection' not in st.session_state:
    st.session_state.selection = "Home"
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'uploaded_students' not in st.session_state:
    st.session_state.uploaded_students = []
if 'attendance_map' not in st.session_state:
    st.session_state.attendance_map = {}

def handle_nav(target):
    st.session_state.selection = target

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

# --- 4. SIDEBAR (FIXED: Added Login/Register to pages list) ---
with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    
    # Define all possible pages so the radio widget doesn't crash
    all_pages = ["Home", "Student Management", "Mark Attendance", "View Reports", "Analytics"]
    if st.session_state.selection not in all_pages:
        # Temporary hidden addition to allow Login/Register to work
        display_pages = all_pages + [st.session_state.selection]
    else:
        display_pages = all_pages

    st.radio("SELECT SECTION", display_pages, key="selection")

# --- 5. PAGE CONTENT ---
if st.session_state.selection == "Home":
    st.markdown('<h1 class="animated-title">AttendX</h1>', unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;'><h2 style='color: #38BDF8;'>Smart Attendance. Real-Time Insights.</h2></div>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 1, 1])
    with col_c:
        target = "Student Management" if st.session_state.authenticated else "Login"
        st.button("🚀 Get Started", use_container_width=True, on_click=handle_nav, args=(target,))
    
    # Rest of Home UI (Cards)...
    f1, f2, f3 = st.columns(3)
    features = [("📱 Digital Marking", "Mark attendance instantly."), ("📊 Smart Reports", "Generate automated insights."), ("🏷️ Auto-Grading", "Intelligent A-D grading.")]
    for i, (title, desc) in enumerate(features):
        with [f1, f2, f3][i]:
            st.markdown(f'<div class="feature-card"><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)

# --- LOGIN PAGE ---
elif st.session_state.selection == "Login":
    st.header("👤 Teacher Login")
    with st.container(border=True):
        st.text_input("user id :", key="login_id")
        st.text_input("password :", type="password", key="login_pw")
        if st.button("Submit Login", type="primary"):
            st.session_state.authenticated = True
            st.session_state.selection = "Home"
            st.success("Login Successful!")
            st.rerun()

# --- REGISTER PAGE ---
elif st.session_state.selection == "Register":
    st.header("📝 Create Teacher Account")
    with st.container(border=True):
        st.text_input("first name", key="reg_fn")
        st.text_input("last name", key="reg_ln")
        st.text_input("e-mail id :", key="reg_email")
        st.text_input("password:", type="password", key="reg_pw")
        if st.button("Submit Registration", type="primary"):
            st.success("Registration Successful! Now please login.")
            st.session_state.selection = "Login"
            st.rerun()

# --- STUDENT MANAGEMENT ---
elif st.session_state.selection == "Student Management":
    st.header("📂 Student Management")
    if not st.session_state.authenticated:
        st.warning("🔒 Please Login to access Student Management.")
    else:
        uploaded_file = st.file_uploader("Upload Student Details (CSV)", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.session_state.uploaded_students = df.to_dict('records')
            st.success("Students Uploaded!")

# (Include Mark Attendance, Reports, Analytics logic here...)

# --- FOOTER ---
st.markdown(f"""
    <div class="footer-container">
        <div class="footer-content" style="display:flex; justify-content: space-between; padding: 40px;">
            <div>
                <h4 style="color:#2563EB;">🏢 AttendX Headquarters</h4>
                <p>Cyber Towers, Hyderabad</p>
                <p>Phone: +91 7386895943</p>
            </div>
            <div style="text-align: right;">
                <h4 style="color:#38BDF8;">Designed by Ganesh Basani</h4>
                <p>© 2025 All Rights Reserved.</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)
