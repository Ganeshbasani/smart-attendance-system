import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from attendance import save_attendance

# --- 1. APP IDENTITY & THEME CONFIG ---
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
    .footer-content {
        max-width: 1200px; margin: 0 auto; display: flex;
        justify-content: space-between; align-items: flex-start; padding: 0 20px;
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

def handle_nav(target):
    st.session_state.selection = target

# --- 3. TOP RIGHT AUTH ICONS ---
c_space, c_login, c_reg = st.columns([7, 1.5, 1.5])
with c_login:
    if not st.session_state.authenticated:
        if st.button("👤 Login", use_container_width=True): st.session_state.selection = "Login"
    else:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.selection = "Home"
            st.rerun()
with c_reg:
    if not st.session_state.authenticated:
        if st.button("📝 Register", use_container_width=True): st.session_state.selection = "Register"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #2563EB;'>AttendX</h1>", unsafe_allow_html=True)
    st.radio("SELECT SECTION", ["Home", "Student Management", "Mark Attendance", "View Reports", "Analytics"], key="selection")

# --- 5. PAGE CONTENT ---
if st.session_state.selection == "Home":
    st.markdown('<h1 class="animated-title">AttendX</h1>', unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;'><h2 style='color: #38BDF8;'>Smart Attendance. Real-Time Insights.</h2></div>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 1, 1])
    with col_c:
        target = "Student Management" if st.session_state.authenticated else "Login"
        st.button("🚀 Get Started", use_container_width=True, on_click=handle_nav, args=(target,))

# --- LOGIN PAGE ---
elif st.session_state.selection == "Login":
    st.header("👤 Teacher Login")
    with st.container(border=True):
        st.text_input("user id :")
        st.text_input("password :", type="password")
        if st.button("Submit Login", type="primary"):
            st.session_state.authenticated = True
            st.session_state.selection = "Home"
            st.success("Login Successful! Welcome back.")
            st.balloons()

# --- REGISTER PAGE ---
elif st.session_state.selection == "Register":
    st.header("📝 Create Teacher Account")
    with st.container(border=True):
        st.text_input("first name")
        st.text_input("last name")
        st.text_input("e-mail id :")
        st.text_input("password:", type="password")
        if st.button("Submit Registration", type="primary"):
            st.success("Registration Successful! You can now Login.")
            st.session_state.selection = "Login"

# --- STUDENT MANAGEMENT ---
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
                st.success("Students Uploaded Successfully!")

# (Rest of the logic for Mark Attendance, Reports, and Analytics follows same pattern)

# --- FOOTER ---
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
