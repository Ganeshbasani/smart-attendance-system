"""Add organization sector profile and optional class/section labels.

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-11-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d5e6f7a8b9c"
down_revision: Union[str, None] = "3c4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("classes", sa.Column("level", sa.String(), nullable=True))
    op.add_column("classes", sa.Column("section", sa.String(), nullable=True))
    op.create_index("ix_classes_level", "classes", ["level"], unique=False)
    op.create_index("ix_classes_section", "classes", ["section"], unique=False)
    op.create_table(
        "organization_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sector", sa.String(), nullable=False),
        sa.Column("has_sections", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(
        sa.table(
            "organization_settings",
            sa.column("id", sa.Integer()), sa.column("name", sa.String()),
            sa.column("sector", sa.String()), sa.column("has_sections", sa.Boolean()),
        ),
        [{"id": 1, "name": "My Organization", "sector": "other", "has_sections": True}],
    )


def downgrade() -> None:
    op.drop_table("organization_settings")
    op.drop_index("ix_classes_section", table_name="classes")
    op.drop_index("ix_classes_level", table_name="classes")
    op.drop_column("classes", "section")
    op.drop_column("classes", "level")
