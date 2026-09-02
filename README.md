<div align="center">

# ðŸ“Š AttendX | Smart Attendance System

<p align="center">
  <strong>Modern â€¢ Intelligent â€¢ Analytics-Driven Attendance Management System</strong>
</p>

<p align="center">
A next-generation attendance management platform built with <b>Streamlit</b>, combining an intuitive user interface, secure authentication, automated attendance tracking, and real-time analytics into one powerful application.
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-Web%20App-red?style=for-the-badge&logo=streamlit)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Processing-black?style=for-the-badge&logo=pandas)
![Plotly](https://img.shields.io/badge/Plotly-Analytics-blueviolet?style=for-the-badge&logo=plotly)
![License](https://img.shields.io/badge/License-MIT-success?style=for-the-badge)

</p>

---

### ðŸŒ Live Demo

ðŸ”— **https://smart-attendance-system-a7xmbumokbzp45erk8my2v.streamlit.app/**

# App Showcase
</div>

<img src="./1.png" alt="AttendX Application Screenshot 1" width="900">

<img src="./2.png" alt="AttendX Application Screenshot 2" width="900">

<img src="./3.png" alt="AttendX Application Screenshot 3" width="900">

<img src="./4.png" alt="AttendX Application Screenshot 4" width="900">

<img src="./5.png" alt="AttendX Application Screenshot 5" width="900">
---

# ðŸ“– Overview

AttendX is an intelligent attendance management application developed to simplify classroom attendance, automate record management, and provide actionable insights through interactive analytics.

Instead of maintaining traditional paper registers or spreadsheets, teachers can securely log into the application, upload student records, mark attendance digitally, and instantly generate attendance reports with visual dashboards.

Designed with a modern biometric-inspired interface and cloud-ready architecture, AttendX delivers a fast, responsive, and user-friendly experience suitable for educational institutions.

---

# âœ¨ Features

- ðŸ” Secure Teacher Authentication
- ðŸ‘¨â€ðŸŽ“ Student Management
- ðŸ“‚ CSV Student Import
- âœ… Digital Attendance Marking
- ðŸ” Instant Student Search
- ðŸ“ˆ Attendance Analytics Dashboard
- ðŸ“Š Interactive Charts
- ðŸ“… Daily Reports
- ðŸ“† Monthly Reports
- ðŸ—“ï¸ Yearly Reports
- ðŸŽ¯ Automatic Attendance Grading
- ðŸ“± Responsive User Interface

---

# ðŸ—ï¸ System Architecture

```text
                    Teacher
                       â”‚
                       â–¼
              Streamlit Web Application
                       â”‚
        â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
        â–¼              â–¼              â–¼
 Authentication   Student Module   Attendance Module
        â”‚              â”‚              â”‚
        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                       â–¼
                Attendance Records
                       â”‚
                       â–¼
             Analytics & Reports
```
# âš™ï¸ Technology Stack

| Category | Technologies |
|-----------|--------------|
| Language | Python |
| Framework | Streamlit |
| Data Processing | Pandas |
| Visualization | Plotly |
| Styling | HTML, CSS |
| Data Storage | CSV Files |
| Authentication | Session State |
| Deployment | Streamlit Cloud |

---

# ðŸš€ Core Modules

## ðŸ” Authentication

- Teacher Registration
- Secure Login
- Session Management
- Protected Pages
- Access Control

---

## ðŸ‘¨â€ðŸŽ“ Student Management

- Upload Student CSV
- Automatic Validation
- Student Search
- Dynamic Student List
- Attendance Initialization

---

## âœ… Attendance Tracking

- Present / Absent Marking
- Interactive Student Cards
- Gender-Based Icons
- Real-Time Updates
- Attendance Status

---

## ðŸ“ˆ Analytics Dashboard

- Total Students
- Present Students
- Absent Students
- Attendance Percentage
- Interactive Charts
- Trend Analysis

---

## ðŸ“„ Reports

- Daily Attendance
- Monthly Summary
- Yearly Overview
- Attendance Percentage
- Grade Calculation
- Export Ready Reports

---

# ðŸ“Š Attendance Workflow

```text
Teacher Login
      â”‚
      â–¼
Upload Student CSV
      â”‚
      â–¼
Load Student Records
      â”‚
      â–¼
Mark Attendance
      â”‚
      â–¼
Generate Reports
      â”‚
      â–¼
View Analytics Dashboard
```

---

# ðŸ“‚ Project Structure

```text
smart-attendance-system/

â”œâ”€â”€ app.py
â”œâ”€â”€ pages/
â”‚
â”œâ”€â”€ assets/
â”‚
â”œâ”€â”€ screenshots/
â”‚   â”œâ”€â”€ home.png
â”‚   â”œâ”€â”€ login.png
â”‚   â”œâ”€â”€ register.png
â”‚   â”œâ”€â”€ dashboard.png
â”‚   â”œâ”€â”€ attendance.png
â”‚   â”œâ”€â”€ reports.png
â”‚   â””â”€â”€ students.png
â”‚
â”œâ”€â”€ data/
â”‚
â”œâ”€â”€ requirements.txt
â”‚
â””â”€â”€ README.md
```

---

# ðŸ“ CSV Format

The uploaded CSV file should contain the following columns:

| Name | Student ID | Gender |
|------|------------|---------|
| John Doe | STU001 | Male |
| Jane Smith | STU002 | Female |

---

# ðŸ“ˆ Analytics

AttendX automatically generates:

- ðŸ“Š Attendance Percentage
- ðŸ“… Daily Attendance
- ðŸ“† Monthly Summary
- ðŸ—“ï¸ Yearly Overview
- ðŸ“‰ Attendance Trends
- ðŸ“ˆ Present vs Absent Distribution
- ðŸŽ¯ Attendance Grades

---

# ðŸ”’ Security Features

- Secure Login
- Session Authentication
- Access Restricted Pages
- Data Validation
- Protected Dashboard
- Controlled Navigation

---

# ðŸŒŸ Key Benefits

- Easy to Use
- Modern UI
- Fast Performance
- Automated Attendance
- Interactive Dashboard
- Real-Time Analytics
- Lightweight Application
- Cloud Deployable

---

# ðŸš€ Future Enhancements

- Face Recognition Attendance
- QR Code Attendance
- RFID Integration
- Firebase Database
- Email Notifications
- Student Portal
- Parent Dashboard
- PDF Report Generation
- AI Attendance Prediction
- Mobile Application

---

# ðŸŽ“ Learning Outcomes

This project demonstrates practical knowledge of:

- Python Programming
- Streamlit Development
- Data Processing with Pandas
- Interactive Dashboard Design
- Session Authentication
- Data Visualization
- UI/UX Design
- Software Engineering Principles

---

# ðŸ‘¨â€ðŸ’» Developer

## Ganesh Basani

**Lead Developer & UI Designer**

ðŸŽ“ B.Tech Computer Science & Engineering

ðŸ“§ ganeshbasani43@gmail.com

ðŸ“± +91 7386895943

ðŸŒ Hyderabad, Telangana, India

---

# ðŸ“œ License

This project is developed for educational and demonstration purposes.

Â© 2025 Ganesh Basani. All Rights Reserved.

---

<div align="center">

## â­ If you like this project, don't forget to give it a Star!

</div>

