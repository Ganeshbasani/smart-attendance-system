"""add attendance sessions and decision records

Revision ID: 2b3c4d5e6f70
Revises: e7f8a9b0c1d2
Create Date: 2026-11-22 00:00:00.000000

Additive only. The existing per-day ``attendance`` table is untouched;
session records and verification events are new tables (AttendX Phase 7).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2b3c4d5e6f70'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'attendance_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_section_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('scheduled_start', sa.DateTime(), nullable=True),
        sa.Column('scheduled_end', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['class_section_id'], ['classes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_attendance_sessions_id', 'attendance_sessions', ['id'], unique=False)
    op.create_index('ix_attendance_sessions_name', 'attendance_sessions', ['name'], unique=False)
    op.create_index('ix_attendance_sessions_status', 'attendance_sessions', ['status'], unique=False)

    op.create_table(
        'session_attendance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('liveness_ok', sa.Boolean(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('marked_by', sa.Integer(), nullable=True),
        sa.Column('marked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['marked_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'user_id', name='uq_session_user'),
    )
    op.create_index('ix_session_attendance_id', 'session_attendance', ['id'], unique=False)
    op.create_index('ix_session_attendance_session_id', 'session_attendance', ['session_id'], unique=False)
    op.create_index('ix_session_attendance_user_id', 'session_attendance', ['user_id'], unique=False)
    op.create_index('ix_session_attendance_decision', 'session_attendance', ['decision'], unique=False)

    op.create_table(
        'verification_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_unique_id', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('liveness_ok', sa.Boolean(), nullable=True),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_verification_events_id', 'verification_events', ['id'], unique=False)
    op.create_index('ix_verification_events_session_id', 'verification_events', ['session_id'], unique=False)
    op.create_index('ix_verification_events_user_id', 'verification_events', ['user_id'], unique=False)
    op.create_index('ix_verification_events_created_at', 'verification_events', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_verification_events_created_at', table_name='verification_events')
    op.drop_index('ix_verification_events_user_id', table_name='verification_events')
    op.drop_index('ix_verification_events_session_id', table_name='verification_events')
    op.drop_index('ix_verification_events_id', table_name='verification_events')
    op.drop_table('verification_events')
    op.drop_index('ix_session_attendance_decision', table_name='session_attendance')
    op.drop_index('ix_session_attendance_user_id', table_name='session_attendance')
    op.drop_index('ix_session_attendance_session_id', table_name='session_attendance')
    op.drop_index('ix_session_attendance_id', table_name='session_attendance')
    op.drop_table('session_attendance')
    op.drop_index('ix_attendance_sessions_status', table_name='attendance_sessions')
    op.drop_index('ix_attendance_sessions_name', table_name='attendance_sessions')
    op.drop_index('ix_attendance_sessions_id', table_name='attendance_sessions')
    op.drop_table('attendance_sessions')
