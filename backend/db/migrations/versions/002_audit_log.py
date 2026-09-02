"""agregar tabla audit_log para auditoría de cambios

Revision ID: 002_audit_log
Revises: 001_initial
Create Date: 2026-09-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_audit_log"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tabla", sa.Text(), nullable=False),
        sa.Column("registro_id", sa.Integer(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("valores_anteriores", sa.JSON(), nullable=True),
        sa.Column("valores_nuevos", sa.JSON(), nullable=True),
        sa.Column("origen", sa.Text(), nullable=False, server_default="whatsapp"),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_index("ix_audit_log_tabla_registro", "audit_log", ["tabla", "registro_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_tabla_registro", table_name="audit_log")
    op.drop_table("audit_log")
