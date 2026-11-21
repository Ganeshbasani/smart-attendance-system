"""add academic domain (AttendX phase 2)

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-11-21 00:00:00.000000

Additive only: no existing column is altered or dropped. Legacy accounts
with role='user' are migrated to 'student' (ADRs 005).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_departments_id', 'departments', ['id'], unique=False)
    op.create_index('ix_departments_name', 'departments', ['name'], unique=True)
    op.create_index('ix_departments_code', 'departments', ['code'], unique=True)

    op.create_table(
        'academic_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_academic_sessions_id', 'academic_sessions', ['id'], unique=False)
    op.create_index('ix_academic_sessions_name', 'academic_sessions', ['name'], unique=True)

    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_courses_id', 'courses', ['id'], unique=False)
    op.create_index('ix_courses_name', 'courses', ['name'], unique=False)
    op.create_index('ix_courses_code', 'courses', ['code'], unique=True)

    op.create_table(
        'teachers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.String(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teachers_id', 'teachers', ['id'], unique=False)
    op.create_index('ix_teachers_user_id', 'teachers', ['user_id'], unique=True)
    op.create_index('ix_teachers_employee_id', 'teachers', ['employee_id'], unique=True)

    op.create_table(
        'students',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('roll_number', sa.String(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('academic_session_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['academic_session_id'], ['academic_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_students_id', 'students', ['id'], unique=False)
    op.create_index('ix_students_user_id', 'students', ['user_id'], unique=True)
    op.create_index('ix_students_roll_number', 'students', ['roll_number'], unique=True)

    op.create_table(
        'classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=True),
        sa.Column('teacher_id', sa.Integer(), nullable=True),
        sa.Column('academic_session_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['academic_session_id'], ['academic_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_classes_id', 'classes', ['id'], unique=False)
    op.create_index('ix_classes_name', 'classes', ['name'], unique=False)
    op.create_index('ix_classes_code', 'classes', ['code'], unique=True)

    op.create_table(
        'class_enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_section_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['class_section_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('class_section_id', 'student_id', name='uq_class_student'),
    )
    op.create_index('ix_class_enrollments_id', 'class_enrollments', ['id'], unique=False)
    op.create_index('ix_class_enrollments_class_section_id', 'class_enrollments', ['class_section_id'], unique=False)
    op.create_index('ix_class_enrollments_student_id', 'class_enrollments', ['student_id'], unique=False)

    # Legacy role migration: existing 'user' accounts become students.
    op.execute("UPDATE users SET role = 'student' WHERE role = 'user'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'user' WHERE role = 'student'")
    op.drop_index('ix_class_enrollments_student_id', table_name='class_enrollments')
    op.drop_index('ix_class_enrollments_class_section_id', table_name='class_enrollments')
    op.drop_index('ix_class_enrollments_id', table_name='class_enrollments')
    op.drop_table('class_enrollments')
    op.drop_index('ix_classes_code', table_name='classes')
    op.drop_index('ix_classes_name', table_name='classes')
    op.drop_index('ix_classes_id', table_name='classes')
    op.drop_table('classes')
    op.drop_index('ix_students_roll_number', table_name='students')
    op.drop_index('ix_students_user_id', table_name='students')
    op.drop_index('ix_students_id', table_name='students')
    op.drop_table('students')
    op.drop_index('ix_teachers_employee_id', table_name='teachers')
    op.drop_index('ix_teachers_user_id', table_name='teachers')
    op.drop_index('ix_teachers_id', table_name='teachers')
    op.drop_table('teachers')
    op.drop_index('ix_courses_code', table_name='courses')
    op.drop_index('ix_courses_name', table_name='courses')
    op.drop_index('ix_courses_id', table_name='courses')
    op.drop_table('courses')
    op.drop_index('ix_academic_sessions_name', table_name='academic_sessions')
    op.drop_index('ix_academic_sessions_id', table_name='academic_sessions')
    op.drop_table('academic_sessions')
    op.drop_index('ix_departments_code', table_name='departments')
    op.drop_index('ix_departments_name', table_name='departments')
    op.drop_index('ix_departments_id', table_name='departments')
    op.drop_table('departments')
