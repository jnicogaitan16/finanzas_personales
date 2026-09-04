"""add tarjetas_credito table and tarjeta_id to compras_cuotas

Revision ID: 71027dcba306
Revises: 004_enhanced_model
Create Date: 2026-09-03 19:29:45.996241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '71027dcba306'
down_revision: Union[str, Sequence[str], None] = '004_enhanced_model'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('tarjetas_credito',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('banco', sa.Text(), nullable=False),
        sa.Column('nombre', sa.Text(), nullable=False),
        sa.Column('ultimos_4', sa.Text(), nullable=True),
        sa.Column('fecha_corte', sa.Integer(), nullable=False),
        sa.Column('fecha_pago', sa.Integer(), nullable=False),
        sa.Column('tasa_ea', sa.Float(), nullable=True),
        sa.Column('cupo_total_cop', sa.Integer(), nullable=True),
        sa.Column('activa', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'nombre', name='uq_tarjeta_user_nombre'),
    )
    op.create_index('ix_tarjetas_credito_user_id', 'tarjetas_credito', ['user_id'])

    op.add_column('compras_cuotas', sa.Column('tarjeta_id', sa.Integer(), nullable=True))
    op.add_column('compras_cuotas', sa.Column('fecha_primera_cuota', sa.Date(), nullable=True))
    op.create_index('ix_compras_cuotas_tarjeta_id', 'compras_cuotas', ['tarjeta_id'])
    op.create_foreign_key(
        'fk_compras_cuotas_tarjeta_id',
        'compras_cuotas', 'tarjetas_credito',
        ['tarjeta_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_compras_cuotas_tarjeta_id', 'compras_cuotas', type_='foreignkey')
    op.drop_index('ix_compras_cuotas_tarjeta_id', table_name='compras_cuotas')
    op.drop_column('compras_cuotas', 'fecha_primera_cuota')
    op.drop_column('compras_cuotas', 'tarjeta_id')
    op.drop_index('ix_tarjetas_credito_user_id', table_name='tarjetas_credito')
    op.drop_table('tarjetas_credito')
