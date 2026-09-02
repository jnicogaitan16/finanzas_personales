"""esquema inicial: users, categorias, movimientos, presupuestos

Revision ID: 001_initial
Revises:
Create Date: 2026-08-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from db.seed import CATEGORIAS_INICIALES

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("numero_whatsapp", sa.Text(), nullable=False),
        sa.UniqueConstraint("numero_whatsapp", name="uq_users_numero_whatsapp"),
    )

    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False, server_default="gasto"),
        sa.UniqueConstraint("nombre", name="uq_categorias_nombre"),
        sa.CheckConstraint("tipo IN ('gasto', 'ingreso')", name="ck_categorias_tipo"),
    )

    op.create_table(
        "movimientos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("monto_cop", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("mensaje_original", sa.Text(), nullable=False),
        sa.Column("fue_audio", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confianza_parsing", sa.Float(), nullable=True),
        sa.Column(
            "fecha_registro",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("fecha_gasto", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_movimientos_user_id"),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["categorias.id"],
            name="fk_movimientos_categoria_id",
        ),
    )
    op.create_index("ix_movimientos_user_id", "movimientos", ["user_id"])
    op.create_index("ix_movimientos_categoria_id", "movimientos", ["categoria_id"])
    op.create_index("ix_movimientos_fecha_gasto", "movimientos", ["fecha_gasto"])

    op.create_table(
        "presupuestos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("monto_limite_cop", sa.Integer(), nullable=False),
        sa.Column("mes_vigente", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_presupuestos_user_id"),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["categorias.id"],
            name="fk_presupuestos_categoria_id",
        ),
        sa.UniqueConstraint(
            "user_id",
            "categoria_id",
            "mes_vigente",
            name="uq_presupuesto_user_categoria_mes",
        ),
    )
    op.create_index("ix_presupuestos_user_id", "presupuestos", ["user_id"])
    op.create_index("ix_presupuestos_categoria_id", "presupuestos", ["categoria_id"])

    categorias = sa.table(
        "categorias",
        sa.column("nombre", sa.Text),
        sa.column("tipo", sa.Text),
    )
    op.bulk_insert(categorias, CATEGORIAS_INICIALES)


def downgrade() -> None:
    op.drop_index("ix_presupuestos_categoria_id", table_name="presupuestos")
    op.drop_index("ix_presupuestos_user_id", table_name="presupuestos")
    op.drop_table("presupuestos")
    op.drop_index("ix_movimientos_fecha_gasto", table_name="movimientos")
    op.drop_index("ix_movimientos_categoria_id", table_name="movimientos")
    op.drop_index("ix_movimientos_user_id", table_name="movimientos")
    op.drop_table("movimientos")
    op.drop_table("categorias")
    op.drop_table("users")
