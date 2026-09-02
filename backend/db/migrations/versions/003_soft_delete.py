"""agregar columna eliminado_en para soft delete de movimientos

Revision ID: 003_soft_delete
Revises: 002_audit_log
Create Date: 2026-09-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_soft_delete"
down_revision: Union[str, Sequence[str], None] = "002_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("movimientos", sa.Column("eliminado_en", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("movimientos", "eliminado_en")
