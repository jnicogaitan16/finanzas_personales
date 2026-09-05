"""cleanup orphan columns add email

Revision ID: 8eaf7fb9b4de
Revises: 382ac2f6dbb4
Create Date: 2026-09-04 15:06:44.941258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '8eaf7fb9b4de'
down_revision: Union[str, Sequence[str], None] = '382ac2f6dbb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Migrar mensaje_original → marca_dedup (copiar datos de dedup antes de eliminar)
    if _column_exists(conn, 'movimientos', 'mensaje_original'):
        op.add_column('movimientos', sa.Column('marca_dedup', sa.Text(), nullable=True))
        op.execute("""
            UPDATE movimientos SET marca_dedup = mensaje_original
            WHERE mensaje_original LIKE 'ingreso_fijo:%'
        """)
        op.drop_column('movimientos', 'mensaje_original')
    if _column_exists(conn, 'movimientos', 'fue_audio'):
        op.drop_column('movimientos', 'fue_audio')
    if _column_exists(conn, 'movimientos', 'confianza_parsing'):
        op.drop_column('movimientos', 'confianza_parsing')

    # Users: quitar numero_whatsapp, agregar email
    if not _column_exists(conn, 'users', 'email'):
        op.add_column('users', sa.Column('email', sa.Text(), nullable=True))
    if _constraint_exists(conn, 'users_numero_whatsapp_key'):
        op.drop_constraint('users_numero_whatsapp_key', 'users', type_='unique')
    if _column_exists(conn, 'users', 'numero_whatsapp'):
        op.drop_column('users', 'numero_whatsapp')
    if not _constraint_exists(conn, 'uq_users_email'):
        op.create_unique_constraint('uq_users_email', 'users', ['email'])

    # CompraCuotas: quitar columna tarjeta texto redundante
    if _column_exists(conn, 'compras_cuotas', 'tarjeta'):
        op.drop_column('compras_cuotas', 'tarjeta')


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _constraint_exists(conn, name: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = :n"
    ), {"n": name})
    return result.fetchone() is not None


def downgrade() -> None:
    op.add_column('compras_cuotas', sa.Column('tarjeta', sa.TEXT(), nullable=True))

    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.add_column('users', sa.Column('numero_whatsapp', sa.TEXT(), nullable=True))
    op.drop_column('users', 'email')

    op.add_column('movimientos', sa.Column('mensaje_original', sa.TEXT(), nullable=True))
    op.execute("UPDATE movimientos SET mensaje_original = COALESCE(marca_dedup, descripcion, 'migrado')")
    op.execute("ALTER TABLE movimientos ALTER COLUMN mensaje_original SET NOT NULL")
    op.add_column('movimientos', sa.Column('confianza_parsing', sa.Float(), nullable=True))
    op.add_column('movimientos', sa.Column('fue_audio', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False))
    op.drop_column('movimientos', 'marca_dedup')
