"""Add attendance mode and explicit manual present/absent status.

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f70
Create Date: 2026-11-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, None] = "2b3c4d5e6f70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendance_sessions",
        sa.Column("attendance_mode", sa.String(), nullable=False, server_default="biometric"),
    )
    op.create_index(
        "ix_attendance_sessions_attendance_mode", "attendance_sessions", ["attendance_mode"]
    )
    op.add_column("session_attendance", sa.Column("attendance_status", sa.String(), nullable=True))
    op.create_index("ix_session_attendance_attendance_status", "session_attendance", ["attendance_status"])


def downgrade() -> None:
    op.drop_index("ix_session_attendance_attendance_status", table_name="session_attendance")
    op.drop_column("session_attendance", "attendance_status")
    op.drop_index("ix_attendance_sessions_attendance_mode", table_name="attendance_sessions")
    op.drop_column("attendance_sessions", "attendance_mode")
