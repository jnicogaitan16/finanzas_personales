"""modelo enriquecido: compras_cuotas, deudas, gastos_fijos, columnas nuevas, categorias

Revision ID: 004_enhanced_model
Revises: 003_soft_delete
Create Date: 2026-09-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_enhanced_model"
down_revision: Union[str, Sequence[str], None] = "003_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NUEVAS_CATEGORIAS = [
    {"nombre": "Hogar", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Seguridad Social", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Administracion", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Suscripciones", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Tarjeta", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Celular", "tipo": "gasto", "es_fijo": True},
    {"nombre": "GYM", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Ahorro", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Deuda", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Freelance", "tipo": "ingreso", "es_fijo": False},
]


def upgrade() -> None:
    # --- Columna nueva en categorias ---
    op.add_column("categorias", sa.Column("es_fijo", sa.Boolean(), nullable=False, server_default=sa.false()))

    # --- Columnas nuevas en movimientos ---
    op.add_column("movimientos", sa.Column("es_compartido", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("movimientos", sa.Column("porcentaje_compartido", sa.Integer(), nullable=True))
    op.add_column("movimientos", sa.Column("medio_pago", sa.Text(), nullable=True))
    op.add_column("movimientos", sa.Column("compra_cuotas_id", sa.Integer(), nullable=True))

    # --- Tabla compras_cuotas ---
    op.create_table(
        "compras_cuotas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fecha_compra", sa.Date(), nullable=False),
        sa.Column("establecimiento", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("valor_total_cop", sa.Integer(), nullable=False),
        sa.Column("num_cuotas", sa.Integer(), nullable=False),
        sa.Column("cuotas_pagadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valor_cuota_cop", sa.Integer(), nullable=False),
        sa.Column("valor_intereses_cop", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasa_ea", sa.Float(), nullable=True),
        sa.Column("numero_transaccion", sa.Text(), nullable=True),
        sa.Column("tarjeta", sa.Text(), nullable=True),
        sa.Column("saldo_pendiente_cop", sa.Integer(), nullable=False),
        sa.Column("liquidada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fecha_ultima_cuota", sa.Date(), nullable=True),
        sa.Column("eliminado_en", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_compras_cuotas_user_id"),
    )
    op.create_index("ix_compras_cuotas_user_id", "compras_cuotas", ["user_id"])

    # --- FK de movimientos a compras_cuotas (ahora que la tabla existe) ---
    op.create_foreign_key(
        "fk_movimientos_compra_cuotas_id",
        "movimientos",
        "compras_cuotas",
        ["compra_cuotas_id"],
        ["id"],
    )

    # --- Tabla deudas ---
    op.create_table(
        "deudas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False, server_default="personal"),
        sa.Column("acreedor", sa.Text(), nullable=True),
        sa.Column("monto_original_cop", sa.Integer(), nullable=False),
        sa.Column("saldo_cop", sa.Integer(), nullable=False),
        sa.Column("cuota_mensual_cop", sa.Integer(), nullable=True),
        sa.Column("tasa_ea", sa.Float(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_limite", sa.Date(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_deudas_user_id"),
        sa.CheckConstraint("tipo IN ('personal', 'tarjeta', 'credito')", name="ck_deudas_tipo"),
    )
    op.create_index("ix_deudas_user_id", "deudas", ["user_id"])

    # --- Tabla gastos_fijos ---
    op.create_table(
        "gastos_fijos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("monto_cop", sa.Integer(), nullable=False),
        sa.Column("es_compartido", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("porcentaje_compartido", sa.Integer(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("dia_esperado", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_gastos_fijos_user_id"),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"], name="fk_gastos_fijos_categoria_id"),
        sa.UniqueConstraint("user_id", "nombre", name="uq_gasto_fijo_user_nombre"),
    )
    op.create_index("ix_gastos_fijos_user_id", "gastos_fijos", ["user_id"])

    # --- Seed nuevas categorias (ON CONFLICT para idempotencia) ---
    conn = op.get_bind()
    for cat in NUEVAS_CATEGORIAS:
        conn.execute(
            sa.text(
                "INSERT INTO categorias (nombre, tipo, es_fijo) "
                "VALUES (:nombre, :tipo, :es_fijo) "
                "ON CONFLICT (nombre) DO UPDATE SET es_fijo = EXCLUDED.es_fijo"
            ),
            cat,
        )

    # Marcar categorias existentes como fijas donde corresponda
    conn.execute(sa.text("UPDATE categorias SET es_fijo = TRUE WHERE nombre = 'Servicios'"))


def downgrade() -> None:
    op.drop_index("ix_gastos_fijos_user_id", table_name="gastos_fijos")
    op.drop_table("gastos_fijos")
    op.drop_index("ix_deudas_user_id", table_name="deudas")
    op.drop_table("deudas")
    op.drop_constraint("fk_movimientos_compra_cuotas_id", "movimientos", type_="foreignkey")
    op.drop_index("ix_compras_cuotas_user_id", table_name="compras_cuotas")
    op.drop_table("compras_cuotas")
    op.drop_column("movimientos", "compra_cuotas_id")
    op.drop_column("movimientos", "medio_pago")
    op.drop_column("movimientos", "porcentaje_compartido")
    op.drop_column("movimientos", "es_compartido")
    op.drop_column("categorias", "es_fijo")
    # No se borran las categorias nuevas en downgrade (datos no destructivos)
