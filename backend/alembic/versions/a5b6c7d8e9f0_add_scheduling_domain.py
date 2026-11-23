"""add scheduling domain (shifts, holidays, leave, corrections)

Revision ID: a5b6c7d8e9f0
Revises: f4a1c2b3d4e5
Create Date: 2026-11-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, None] = 'f4a1c2b3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── shifts ──
    op.create_table(
        'shifts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('grace_minutes', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_shifts_id', 'shifts', ['id'], unique=False)
    op.create_index('ix_shifts_name', 'shifts', ['name'], unique=True)

    # ── holidays ──
    op.create_table(
        'holidays',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_holidays_id', 'holidays', ['id'], unique=False)
    op.create_index('ix_holidays_date', 'holidays', ['date'], unique=True)

    # ── leave requests ──
    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('leave_type', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_leave_requests_id', 'leave_requests', ['id'], unique=False)
    op.create_index('ix_leave_requests_status', 'leave_requests', ['status'], unique=False)
    op.create_index('ix_leave_requests_user_id', 'leave_requests', ['user_id'], unique=False)

    # ── attendance correction requests ──
    op.create_table(
        'attendance_correction_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('attendance_id', sa.Integer(), nullable=False),
        sa.Column('proposed_status', sa.String(), nullable=False),
        sa.Column('proposed_time_in', sa.Time(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attendance_id'], ['attendance.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_correction_requests_id', 'attendance_correction_requests', ['id'], unique=False)
    op.create_index('ix_correction_requests_status', 'attendance_correction_requests', ['status'], unique=False)
    op.create_index('ix_correction_requests_user_id', 'attendance_correction_requests', ['user_id'], unique=False)

    # ── attendance: checkout + late/early flags ──
    op.add_column('attendance', sa.Column('time_out', sa.Time(), nullable=True))
    op.add_column('attendance', sa.Column('is_late', sa.Boolean(), nullable=True))
    op.add_column('attendance', sa.Column('is_early_leave', sa.Boolean(), nullable=True))

    # ── users: optional shift assignment ──
    # batch_alter_table so the FK works on SQLite (copy-and-move) and emits a
    # plain ALTER on PostgreSQL.
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('shift_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_users_shift_id', 'shifts', ['shift_id'], ['id']
        )
        batch_op.create_index('ix_users_shift_id', ['shift_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('fk_users_shift_id', type_='foreignkey')
        batch_op.drop_index('ix_users_shift_id')
        batch_op.drop_column('shift_id')

    op.drop_column('attendance', 'is_early_leave')
    op.drop_column('attendance', 'is_late')
    op.drop_column('attendance', 'time_out')

    op.drop_index('ix_correction_requests_user_id', table_name='attendance_correction_requests')
    op.drop_index('ix_correction_requests_status', table_name='attendance_correction_requests')
    op.drop_index('ix_correction_requests_id', table_name='attendance_correction_requests')
    op.drop_table('attendance_correction_requests')

    op.drop_index('ix_leave_requests_user_id', table_name='leave_requests')
    op.drop_index('ix_leave_requests_status', table_name='leave_requests')
    op.drop_index('ix_leave_requests_id', table_name='leave_requests')
    op.drop_table('leave_requests')

    op.drop_index('ix_holidays_date', table_name='holidays')
    op.drop_index('ix_holidays_id', table_name='holidays')
    op.drop_table('holidays')

    op.drop_index('ix_shifts_name', table_name='shifts')
    op.drop_index('ix_shifts_id', table_name='shifts')
    op.drop_table('shifts')
