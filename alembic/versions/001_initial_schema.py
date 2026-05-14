"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["departments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"], unique=False)
    op.create_index(
        "uq_dept_parent_name_nn",
        "departments",
        ["parent_id", "name"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )
    op.create_index(
        "uq_dept_root_name",
        "departments",
        ["name"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("position", sa.String(length=200), nullable=False),
        sa.Column("hired_at", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employees_department_id", "employees", ["department_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_employees_department_id", table_name="employees")
    op.drop_table("employees")
    op.drop_index("uq_dept_root_name", table_name="departments")
    op.drop_index("uq_dept_parent_name_nn", table_name="departments")
    op.drop_index("ix_departments_parent_id", table_name="departments")
    op.drop_table("departments")
