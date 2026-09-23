from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import *
from .security import hash_password
import random

DEMO_PASSWORD = "AttendX@2026"

def seed(db: Session):
    if db.scalar(select(User).limit(1)):
        return
    random.seed(42)
    cse = Department(code="CSE", name="Computer Science & Engineering")
    ece = Department(code="ECE", name="Electronics & Communication")
    db.add_all([cse, ece]); db.flush()
    sec_a = Section(name="CSE-A", year=4, department_id=cse.id)
    sec_b = Section(name="CSE-B", year=4, department_id=cse.id)
    db.add_all([sec_a, sec_b]); db.flush()
    subjects = [
        Subject(code="CS401", name="Distributed Systems", department_id=cse.id, semester="VIII", threshold=75, planned_sessions=40),
        Subject(code="CS402", name="Cloud Computing", department_id=cse.id, semester="VIII", threshold=75, planned_sessions=36),
        Subject(code="CS403", name="Machine Learning", department_id=cse.id, semester="VIII", threshold=75, planned_sessions=42),
        Subject(code="CS404", name="DevOps Engineering", department_id=cse.id, semester="VIII", threshold=75, planned_sessions=30),
    ]
    db.add_all(subjects); db.flush()
    admin = User(username="admin", full_name="AttendX Administrator", role="admin", password_hash=hash_password(DEMO_PASSWORD), department_id=cse.id)
    hod = User(username="hod", full_name="Dr. Priya Nair", role="hod", password_hash=hash_password(DEMO_PASSWORD), department_id=cse.id)
    faculty = User(username="faculty", full_name="Arjun Rao", role="faculty", password_hash=hash_password(DEMO_PASSWORD), department_id=cse.id)
    db.add_all([admin, hod, faculty]); db.flush()
    students=[]
    first_names=["Rahul","Priya","Amit","Neha","Arjun","Kavya","Rohit","Sneha","Manish","Anjali","Karan","Pooja","Suresh","Meera","Varun","Riya","Deepak","Nisha","Akash","Isha"]
    for i,name in enumerate(first_names, start=1):
        s=Student(student_id=f"24CSE{i:03d}", name=name, department_id=cse.id, section_id=sec_a.id if i<=10 else sec_b.id, year=4)
        students.append(s)
    db.add_all(students); db.flush()
    student_user = User(username="student", full_name=students[0].name, role="student", password_hash=hash_password(DEMO_PASSWORD), student_id=students[0].student_id, department_id=cse.id)
    db.add(student_user); db.flush()
    for stu in students:
        for subj in subjects:
            db.add(Enrollment(student_id=stu.id, subject_id=subj.id))
    for subj in subjects:
        db.add(FacultyAssignment(faculty_user_id=faculty.id, subject_id=subj.id, section_id=sec_a.id))
        db.add(FacultyAssignment(faculty_user_id=faculty.id, subject_id=subj.id, section_id=sec_b.id))
    weekdays = [0,1,2,3,4]
    for idx, subj in enumerate(subjects):
        db.add(TimetableEntry(section_id=sec_a.id, subject_id=subj.id, faculty_user_id=faculty.id, weekday=weekdays[idx%5], start_time="10:00", end_time="11:00", room=f"B-{200+idx}"))
    db.commit()
    db.add(Intervention(student_id=students[0].student_id, subject_id=subjects[0].id, trigger_type="At Risk", recommendation="Attend the next 6 Distributed Systems sessions and schedule a faculty check-in.", owner_user_id=faculty.id, due_date=date.today()+timedelta(days=10), status="Open"))
    db.add(Notification(user_id=student_user.id, student_id=students[0].student_id, priority="High", title="Distributed Systems needs attention", message="Attendance is below the 75% policy threshold. Your runway currently depends on attending the next recovery window.", dedupe_key="seed:ds:risk"))
    db.commit()
    # Create historical sessions & attendance for the first 20 students.
    base = date.today() - timedelta(days=70)
    for day_idx in range(1, 33):
        d = base + timedelta(days=day_idx*2)
        subj = subjects[day_idx % len(subjects)]
        sec = sec_a if day_idx % 2 else sec_b
        session = ClassSession(subject_id=subj.id, section_id=sec.id, faculty_user_id=faculty.id, session_date=d, start_time="10:00", end_time="11:00", status="closed", qr_secret="seed")
        db.add(session); db.flush()
        for stu in students:
            if stu.section_id != sec.id: continue
            attendance_rate = 0.88
            if stu.student_id == students[0].student_id:
                attendance_rate = {subjects[0].code:0.70, subjects[1].code:0.79, subjects[2].code:0.84, subjects[3].code:0.93}.get(subj.code, 0.8)
            status = "Present" if random.random() < attendance_rate else "Absent"
            db.add(AttendanceRecord(session_id=session.id, student_id=stu.student_id, status=status, source="seed"))
    db.commit()
