# smart-attendance-system


 📊 AttendX | Smart Attendance System

**AttendX** is a state-of-the-art, end-to-end attendance management solution. It bridges the gap between traditional manual record-keeping and modern data science by providing a high-fidelity digital interface combined with automated analytics. Built using the **Streamlit** framework, AttendX is optimized for speed, security, and a premium user experience.

 🌐 Live Deployment

**Experience the system in real-time:** **[AttendX Web App](https://smart-attendance-system-a7xmbumokbzp45erk8my2v.streamlit.app/#attend-x)**

---

🔬 Technical Overview & Architecture

🛡️ Secure Authentication Framework

AttendX implements a session-based security layer. Teachers must undergo a multi-step registration and login process before the system unlocks administrative features.

* **User ID & Password Encryption**: Designed to store and verify teacher credentials.
* **Access Control**: Pages like *Student Management* and *Mark Attendance* are restricted via `st.session_state` to prevent unauthorized data manipulation.

🎨 Design Philosophy (Biometric UI)

The interface is engineered with a "Biometric-First" aesthetic:

* **Layered Background**: A triple-layer CSS approach combining a dark slate gradient, a carbon-fibre texture, and a high-transparency fingerprint overlay.
* **Motion Graphics**: Utilizes CSS keyframe animations (`titleGlow`) to create a professional, breathing effect for the 100px branding.
* **Responsive Layout**: Built with a wide-screen configuration to ensure that student cards and analytics charts maintain a balanced "Golden Ratio" gap for maximum readability.



🛠️ Core Functional Modules

1. Student Management (Data Ingestion)

The teacher acts as the primary data controller. Instead of a static database, AttendX allows for dynamic classroom management:

* **CSV Parsing**: Teachers upload a `.csv` file. The system validates headers (`name`, `student_id`, `gender`) and maps them to the session state.
* **Dynamic Initialization**: Upon upload, the system automatically builds an attendance map, defaulting all students to "Absent" until marked otherwise.

2. Digital Attendance Marking

* **Interactive Cards**: Each student is represented by a card featuring gender-appropriate emojis (`👦` or `👧`).
* **Visual Feedback Logic**:
* **Present**: Status text turns **Green (#22C55E)**.
* **Absent**: Status text turns **Red (#EF4444)**.


* **Search Engine**: A real-time filter allows teachers to find specific students by name instantly within large datasets.

3. Automated Reporting & Grading

The system processes raw attendance data into three distinct temporal views:

* **Daily Log**: A snapshot of current session presence.
* **Monthly Summary**: Calculates "Days Present" vs. "Total Working Days" (defaulting to 22).
* **Yearly Overview**: Long-term tracking (defaulting to 220 days).
* **Auto-Grading System**: Automatically assigns grades (**A, B, C, D**) based on the calculated attendance percentage.

4. Real-Time Analytics Dashboard

* **Distribution Bar Charts**: Compares total present vs. total absent students.
* **Attendance Trends**: A line chart visualizing the consistency of attendance over time.
* **Metric Cards**: High-level summaries (Total Students, Present Count, Attendance Rate).


📂 Data Format Requirements

To ensure the system functions correctly, the uploaded CSV should follow this structure:
| name | student_id | gender |
| :--- | :--- | :--- |
| John Doe | STU001 | Male |
| Jane Smith | STU002 | Female |



👨‍💻 Developer Credits

**Ganesh Basani** *Lead Developer & UI/UX Designer* **Project Year**: 2025

**Institutional Focus**: Academic Excellence in Software Engineering

**Headquarters**: Cyber Towers, Hitech City, Hyderabad

**Contact Information:**

* 📧 **Email**: ganeshbasani43@gmail.com
* 📱 **Phone**: +91 7386895943

---

📜 Legal & License

© 2025 AttendX Smart Attendance System. All Rights Reserved. This project is developed for academic purposes and features original UI designs and logic architecture by Ganesh Basani.
