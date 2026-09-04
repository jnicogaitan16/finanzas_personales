"""add grupos table and auth fields to users

Revision ID: 382ac2f6dbb4
Revises: 8840e4e596d6
Create Date: 2026-09-03 21:02:58.798505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '382ac2f6dbb4'
down_revision: Union[str, Sequence[str], None] = '8840e4e596d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('grupos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.Text(), nullable=False),
        sa.Column('codigo_invitacion', sa.Text(), nullable=True),
        sa.Column('codigo_expira', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo_invitacion'),
    )

    op.add_column('users', sa.Column('password_hash', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('grupo_id', sa.Integer(), nullable=True))
    op.create_index('ix_users_grupo_id', 'users', ['grupo_id'])
    op.create_unique_constraint('uq_users_nombre', 'users', ['nombre'])
    op.create_foreign_key('fk_users_grupo_id', 'users', 'grupos', ['grupo_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_users_grupo_id', 'users', type_='foreignkey')
    op.drop_constraint('uq_users_nombre', 'users', type_='unique')
    op.drop_index('ix_users_grupo_id', table_name='users')
    op.drop_column('users', 'grupo_id')
    op.drop_column('users', 'password_hash')
    op.drop_table('grupos')
