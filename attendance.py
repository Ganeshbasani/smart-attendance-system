import csv
from datetime import date

STUDENT_FILE = "students.csv"
ATTENDANCE_FILE = "attendance.csv"

def load_students():
    students = []
    with open(STUDENT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            students.append(row)
    return students

def save_attendance(attendance_data):
    today = date.today().isoformat()

    with open(ATTENDANCE_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for student_id, status in attendance_data.items():
            writer.writerow([today, student_id, status])
