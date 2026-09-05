"""add metas_ahorro table

Revision ID: a1b2c3d4e5f6
Revises: 8eaf7fb9b4de
Create Date: 2026-09-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '8eaf7fb9b4de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'metas_ahorro',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('nombre', sa.Text(), nullable=False),
        sa.Column('monto_objetivo_cop', sa.Integer(), nullable=False),
        sa.Column('monto_actual_cop', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('fecha_limite', sa.Date(), nullable=True),
        sa.Column('activa', sa.Boolean(), nullable=False, server_default='true'),
        sa.UniqueConstraint('user_id', 'nombre', name='uq_meta_ahorro_user_nombre'),
    )


def downgrade() -> None:
    op.drop_table('metas_ahorro')
