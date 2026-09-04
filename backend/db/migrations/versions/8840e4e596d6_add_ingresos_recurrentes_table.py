"""add ingresos_recurrentes table

Revision ID: 8840e4e596d6
Revises: 71027dcba306
Create Date: 2026-09-03 19:42:25.467194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8840e4e596d6'
down_revision: Union[str, Sequence[str], None] = '71027dcba306'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ingresos_recurrentes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.Text(), nullable=False),
        sa.Column('tipo', sa.Text(), nullable=False),
        sa.Column('frecuencia', sa.Text(), nullable=False),
        sa.Column('monto_cop', sa.Integer(), nullable=False),
        sa.Column('dia_pago_1', sa.Integer(), nullable=True),
        sa.Column('dia_pago_2', sa.Integer(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.CheckConstraint("frecuencia IN ('mensual', 'quincenal', 'semanal', 'anual')", name='ck_ingreso_frecuencia'),
        sa.CheckConstraint("tipo IN ('fijo', 'variable')", name='ck_ingreso_tipo'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'nombre', name='uq_ingreso_user_nombre'),
    )
    op.create_index('ix_ingresos_recurrentes_user_id', 'ingresos_recurrentes', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_ingresos_recurrentes_user_id', table_name='ingresos_recurrentes')
    op.drop_table('ingresos_recurrentes')
