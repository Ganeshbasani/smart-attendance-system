"""Academic domain API (AttendX Phase 2), mounted under ``/api/v1``.

All new endpoints are additive: legacy unversioned routes keep working.
Mutations are admin-only; reads are available to any authenticated user,
with students restricted to their own profile and enrolled classes.
"""

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import get_password_hash, validate_password_strength
from app.core.time_utils import now_local
from app.db.session import get_db
from app.models import (
    AcademicSession,
    ClassEnrollment,
    ClassSection,
    Course,
    Department,
    Student,
    Teacher,
    User,
)
from app.schemas import (
    AcademicSessionCreate,
    AcademicSessionOut,
    ClassSectionCreate,
    ClassSectionOut,
    CourseCreate,
    CourseOut,
    DepartmentCreate,
    DepartmentOut,
    EnrollRequest,
    EnrollmentOut,
    StudentCreate,
    StudentOut,
    TeacherCreate,
    TeacherOut,
)
from app.services.audit import record as audit_record

router = APIRouter(prefix="/api/v1", tags=["academic"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, model, object_id: int, label: str):
    obj = db.query(model).filter(model.id == object_id).first()
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _check_fk(db: Session, model, object_id: Optional[int], label: str) -> None:
    if object_id is not None and db.query(model).filter(model.id == object_id).first() is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")


def _unique_id(prefix: str) -> str:
    return f"{prefix}{now_local().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(2)}"


def _student_out(s: Student) -> StudentOut:
    return StudentOut(
        id=s.id, user_id=s.user_id, roll_number=s.roll_number,
        department_id=s.department_id, academic_session_id=s.academic_session_id,
        email=s.user.email, full_name=s.user.full_name, role=s.user.role,
        created_at=s.created_at,
    )


def _teacher_out(t: Teacher) -> TeacherOut:
    return TeacherOut(
        id=t.id, user_id=t.user_id, employee_id=t.employee_id,
        department_id=t.department_id, email=t.user.email,
        full_name=t.user.full_name, created_at=t.created_at,
    )


def _class_out(db: Session, c: ClassSection) -> ClassSectionOut:
    count = db.query(ClassEnrollment).filter(
        ClassEnrollment.class_section_id == c.id
    ).count()
    return ClassSectionOut(
        id=c.id, name=c.name, code=c.code, course_id=c.course_id,
        teacher_id=c.teacher_id, academic_session_id=c.academic_session_id,
        student_count=count, created_at=c.created_at,
    )


# ── departments ───────────────────────────────────────────────────────────────

@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    return db.query(Department).order_by(Department.name).offset(skip).limit(limit).all()


@router.post("/departments", response_model=DepartmentOut, status_code=201)
async def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    if db.query(Department).filter(Department.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Department name already exists")
    if payload.code and db.query(Department).filter(Department.code == payload.code).first():
        raise HTTPException(status_code=409, detail="Department code already exists")
    dept = Department(name=payload.name, code=payload.code)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    audit_record(db, action="academic.department.create", actor=current_user,
                 entity_type="department", entity_id=str(dept.id), details={"name": dept.name})
    return dept


@router.put("/departments/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: int, payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    dept = _get_or_404(db, Department, department_id, "Department")
    if db.query(Department).filter(Department.name == payload.name, Department.id != department_id).first():
        raise HTTPException(status_code=409, detail="Department name already exists")
    dept.name = payload.name
    dept.code = payload.code
    db.commit()
    db.refresh(dept)
    audit_record(db, action="academic.department.update", actor=current_user,
                 entity_type="department", entity_id=str(dept.id), details={"name": dept.name})
    return dept


@router.delete("/departments/{department_id}", status_code=204)
async def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    dept = _get_or_404(db, Department, department_id, "Department")
    db.delete(dept)
    db.commit()
    audit_record(db, action="academic.department.delete", actor=current_user,
                 entity_type="department", entity_id=str(department_id))
    return Response(status_code=204)


# ── academic sessions ─────────────────────────────────────────────────────────

@router.get("/academic-sessions", response_model=list[AcademicSessionOut])
async def list_academic_sessions(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    return db.query(AcademicSession).order_by(AcademicSession.start_date.desc()).offset(skip).limit(limit).all()


@router.post("/academic-sessions", response_model=AcademicSessionOut, status_code=201)
async def create_academic_session(
    payload: AcademicSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    if db.query(AcademicSession).filter(AcademicSession.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Academic session name already exists")
    session = AcademicSession(
        name=payload.name, start_date=payload.start_date,
        end_date=payload.end_date, is_active=payload.is_active,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    audit_record(db, action="academic.session.create", actor=current_user,
                 entity_type="academic_session", entity_id=str(session.id), details={"name": session.name})
    return session


@router.put("/academic-sessions/{session_id}", response_model=AcademicSessionOut)
async def update_academic_session(
    session_id: int, payload: AcademicSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    session = _get_or_404(db, AcademicSession, session_id, "Academic session")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    if db.query(AcademicSession).filter(
        AcademicSession.name == payload.name, AcademicSession.id != session_id
    ).first():
        raise HTTPException(status_code=409, detail="Academic session name already exists")
    session.name = payload.name
    session.start_date = payload.start_date
    session.end_date = payload.end_date
    session.is_active = payload.is_active
    db.commit()
    db.refresh(session)
    audit_record(db, action="academic.session.update", actor=current_user,
                 entity_type="academic_session", entity_id=str(session.id))
    return session


@router.delete("/academic-sessions/{session_id}", status_code=204)
async def delete_academic_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    session = _get_or_404(db, AcademicSession, session_id, "Academic session")
    db.delete(session)
    db.commit()
    audit_record(db, action="academic.session.delete", actor=current_user,
                 entity_type="academic_session", entity_id=str(session_id))
    return Response(status_code=204)


# ── courses ───────────────────────────────────────────────────────────────────

@router.get("/courses", response_model=list[CourseOut])
async def list_courses(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    return db.query(Course).order_by(Course.code).offset(skip).limit(limit).all()


@router.post("/courses", response_model=CourseOut, status_code=201)
async def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    if db.query(Course).filter(Course.code == payload.code).first():
        raise HTTPException(status_code=409, detail="Course code already exists")
    _check_fk(db, Department, payload.department_id, "Department")
    course = Course(
        name=payload.name, code=payload.code,
        department_id=payload.department_id, credits=payload.credits,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    audit_record(db, action="academic.course.create", actor=current_user,
                 entity_type="course", entity_id=str(course.id), details={"code": course.code})
    return course


@router.put("/courses/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int, payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    course = _get_or_404(db, Course, course_id, "Course")
    if db.query(Course).filter(Course.code == payload.code, Course.id != course_id).first():
        raise HTTPException(status_code=409, detail="Course code already exists")
    _check_fk(db, Department, payload.department_id, "Department")
    course.name = payload.name
    course.code = payload.code
    course.department_id = payload.department_id
    course.credits = payload.credits
    db.commit()
    db.refresh(course)
    audit_record(db, action="academic.course.update", actor=current_user,
                 entity_type="course", entity_id=str(course.id))
    return course


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    course = _get_or_404(db, Course, course_id, "Course")
    db.delete(course)
    db.commit()
    audit_record(db, action="academic.course.delete", actor=current_user,
                 entity_type="course", entity_id=str(course_id))
    return Response(status_code=204)


# ── teachers ──────────────────────────────────────────────────────────────────

@router.get("/teachers", response_model=list[TeacherOut])
async def list_teachers(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    teachers = db.query(Teacher).order_by(Teacher.employee_id).offset(skip).limit(limit).all()
    return [_teacher_out(t) for t in teachers]


@router.post("/teachers", response_model=TeacherOut, status_code=201)
async def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    validate_password_strength(payload.password)
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    if db.query(Teacher).filter(Teacher.employee_id == payload.employee_id).first():
        raise HTTPException(status_code=409, detail="Employee ID already exists")
    _check_fk(db, Department, payload.department_id, "Department")
    user = User(
        email=payload.email, password=get_password_hash(payload.password),
        full_name=payload.full_name, unique_id=_unique_id("TCH"),
        phone_number=payload.phone_number, role="teacher", is_active=True,
    )
    db.add(user)
    db.flush()
    teacher = Teacher(
        user_id=user.id, employee_id=payload.employee_id,
        department_id=payload.department_id,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    audit_record(db, action="academic.teacher.create", actor=current_user,
                 entity_type="teacher", entity_id=str(teacher.id), details={"employee_id": teacher.employee_id})
    return _teacher_out(teacher)


@router.get("/teachers/{teacher_id}", response_model=TeacherOut)
async def get_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    return _teacher_out(_get_or_404(db, Teacher, teacher_id, "Teacher"))


@router.put("/teachers/{teacher_id}", response_model=TeacherOut)
async def update_teacher(
    teacher_id: int, payload: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    teacher = _get_or_404(db, Teacher, teacher_id, "Teacher")
    if db.query(Teacher).filter(
        Teacher.employee_id == payload.employee_id, Teacher.id != teacher_id
    ).first():
        raise HTTPException(status_code=409, detail="Employee ID already exists")
    _check_fk(db, Department, payload.department_id, "Department")
    teacher.employee_id = payload.employee_id
    teacher.department_id = payload.department_id
    teacher.user.full_name = payload.full_name
    teacher.user.phone_number = payload.phone_number
    db.commit()
    db.refresh(teacher)
    audit_record(db, action="academic.teacher.update", actor=current_user,
                 entity_type="teacher", entity_id=str(teacher.id))
    return _teacher_out(teacher)


@router.delete("/teachers/{teacher_id}", status_code=204)
async def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    teacher = _get_or_404(db, Teacher, teacher_id, "Teacher")
    user = teacher.user
    db.delete(user)  # cascades to the teacher profile and all user data
    db.commit()
    audit_record(db, action="academic.teacher.delete", actor=current_user,
                 entity_type="teacher", entity_id=str(teacher_id))
    return Response(status_code=204)


# ── students ──────────────────────────────────────────────────────────────────

@router.get("/students", response_model=list[StudentOut])
async def list_students(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    query = db.query(Student)
    if current_user.role not in ("admin", "teacher"):
        # Students only ever see their own profile through this endpoint.
        query = query.filter(Student.user_id == current_user.id)
    students = query.order_by(Student.roll_number).offset(skip).limit(limit).all()
    return [_student_out(s) for s in students]


@router.get("/students/me", response_model=StudentOut)
async def get_my_student_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_student),
):
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return _student_out(student)


@router.post("/students", response_model=StudentOut, status_code=201)
async def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    validate_password_strength(payload.password)
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    if db.query(Student).filter(Student.roll_number == payload.roll_number).first():
        raise HTTPException(status_code=409, detail="Roll number already exists")
    _check_fk(db, Department, payload.department_id, "Department")
    _check_fk(db, AcademicSession, payload.academic_session_id, "Academic session")
    user = User(
        email=payload.email, password=get_password_hash(payload.password),
        full_name=payload.full_name, unique_id=_unique_id("STU"),
        phone_number=payload.phone_number, role="student", is_active=True,
    )
    db.add(user)
    db.flush()
    student = Student(
        user_id=user.id, roll_number=payload.roll_number,
        department_id=payload.department_id,
        academic_session_id=payload.academic_session_id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    audit_record(db, action="academic.student.create", actor=current_user,
                 entity_type="student", entity_id=str(student.id),
                 details={"roll_number": student.roll_number})
    return _student_out(student)


@router.get("/students/{student_id}", response_model=StudentOut)
async def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    student = _get_or_404(db, Student, student_id, "Student")
    if current_user.role not in ("admin", "teacher") and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view another student")
    return _student_out(student)


@router.put("/students/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: int, payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    student = _get_or_404(db, Student, student_id, "Student")
    if db.query(Student).filter(
        Student.roll_number == payload.roll_number, Student.id != student_id
    ).first():
        raise HTTPException(status_code=409, detail="Roll number already exists")
    _check_fk(db, Department, payload.department_id, "Department")
    _check_fk(db, AcademicSession, payload.academic_session_id, "Academic session")
    student.roll_number = payload.roll_number
    student.department_id = payload.department_id
    student.academic_session_id = payload.academic_session_id
    student.user.full_name = payload.full_name
    student.user.phone_number = payload.phone_number
    db.commit()
    db.refresh(student)
    audit_record(db, action="academic.student.update", actor=current_user,
                 entity_type="student", entity_id=str(student.id))
    return _student_out(student)


@router.delete("/students/{student_id}", status_code=204)
async def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    student = _get_or_404(db, Student, student_id, "Student")
    user = student.user
    db.delete(user)  # cascades to face data, attendance, enrollments, profile
    db.commit()
    audit_record(db, action="academic.student.delete", actor=current_user,
                 entity_type="student", entity_id=str(student_id))
    return Response(status_code=204)


# ── classes and enrollments ───────────────────────────────────────────────────

@router.get("/classes", response_model=list[ClassSectionOut])
async def list_classes(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    query = db.query(ClassSection)
    if current_user.role not in ("admin", "teacher"):
        # Students see only classes they are enrolled in.
        query = query.join(ClassEnrollment).join(Student).filter(Student.user_id == current_user.id)
    classes = query.order_by(ClassSection.code).offset(skip).limit(limit).all()
    return [_class_out(db, c) for c in classes]


@router.post("/classes", response_model=ClassSectionOut, status_code=201)
async def create_class(
    payload: ClassSectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    if db.query(ClassSection).filter(ClassSection.code == payload.code).first():
        raise HTTPException(status_code=409, detail="Class code already exists")
    _check_fk(db, Course, payload.course_id, "Course")
    _check_fk(db, Teacher, payload.teacher_id, "Teacher")
    _check_fk(db, AcademicSession, payload.academic_session_id, "Academic session")
    section = ClassSection(
        name=payload.name, code=payload.code, course_id=payload.course_id,
        teacher_id=payload.teacher_id, academic_session_id=payload.academic_session_id,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    audit_record(db, action="academic.class.create", actor=current_user,
                 entity_type="class", entity_id=str(section.id), details={"code": section.code})
    return _class_out(db, section)


@router.get("/classes/{class_id}", response_model=ClassSectionOut)
async def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    section = _get_or_404(db, ClassSection, class_id, "Class")
    if current_user.role not in ("admin", "teacher"):
        enrolled = db.query(ClassEnrollment).join(Student).filter(
            ClassEnrollment.class_section_id == class_id,
            Student.user_id == current_user.id,
        ).first()
        if enrolled is None:
            raise HTTPException(status_code=403, detail="Not enrolled in this class")
    return _class_out(db, section)


@router.put("/classes/{class_id}", response_model=ClassSectionOut)
async def update_class(
    class_id: int, payload: ClassSectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    section = _get_or_404(db, ClassSection, class_id, "Class")
    if db.query(ClassSection).filter(
        ClassSection.code == payload.code, ClassSection.id != class_id
    ).first():
        raise HTTPException(status_code=409, detail="Class code already exists")
    _check_fk(db, Course, payload.course_id, "Course")
    _check_fk(db, Teacher, payload.teacher_id, "Teacher")
    _check_fk(db, AcademicSession, payload.academic_session_id, "Academic session")
    section.name = payload.name
    section.code = payload.code
    section.course_id = payload.course_id
    section.teacher_id = payload.teacher_id
    section.academic_session_id = payload.academic_session_id
    db.commit()
    db.refresh(section)
    audit_record(db, action="academic.class.update", actor=current_user,
                 entity_type="class", entity_id=str(section.id))
    return _class_out(db, section)


@router.delete("/classes/{class_id}", status_code=204)
async def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    section = _get_or_404(db, ClassSection, class_id, "Class")
    db.delete(section)  # cascades to enrollments
    db.commit()
    audit_record(db, action="academic.class.delete", actor=current_user,
                 entity_type="class", entity_id=str(class_id))
    return Response(status_code=204)


@router.get("/classes/{class_id}/students", response_model=list[EnrollmentOut])
async def list_class_students(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _get_or_404(db, ClassSection, class_id, "Class")
    rows = db.query(ClassEnrollment).join(Student).join(User).filter(
        ClassEnrollment.class_section_id == class_id
    ).all()
    return [
        EnrollmentOut(
            id=r.id, class_section_id=r.class_section_id, student_id=r.student_id,
            roll_number=r.student.roll_number, full_name=r.student.user.full_name,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/classes/{class_id}/enrollments", response_model=EnrollmentOut, status_code=201)
async def enroll_student(
    class_id: int, payload: EnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    _get_or_404(db, ClassSection, class_id, "Class")
    student = _get_or_404(db, Student, payload.student_id, "Student")
    if db.query(ClassEnrollment).filter(
        ClassEnrollment.class_section_id == class_id,
        ClassEnrollment.student_id == student.id,
    ).first():
        raise HTTPException(status_code=409, detail="Student already enrolled in this class")
    enrollment = ClassEnrollment(class_section_id=class_id, student_id=student.id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    audit_record(db, action="academic.class.enroll", actor=current_user,
                 entity_type="class", entity_id=str(class_id),
                 details={"student_id": student.id, "roll_number": student.roll_number})
    return EnrollmentOut(
        id=enrollment.id, class_section_id=class_id, student_id=student.id,
        roll_number=student.roll_number, full_name=student.user.full_name,
        created_at=enrollment.created_at,
    )


@router.delete("/classes/{class_id}/enrollments/{student_id}", status_code=204)
async def unenroll_student(
    class_id: int, student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    _get_or_404(db, ClassSection, class_id, "Class")
    enrollment = db.query(ClassEnrollment).filter(
        ClassEnrollment.class_section_id == class_id,
        ClassEnrollment.student_id == student_id,
    ).first()
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    db.delete(enrollment)
    db.commit()
    audit_record(db, action="academic.class.unenroll", actor=current_user,
                 entity_type="class", entity_id=str(class_id),
                 details={"student_id": student_id})
    return Response(status_code=204)
