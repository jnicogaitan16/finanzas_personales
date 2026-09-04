from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Grupo(Base):
    __tablename__ = "grupos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    codigo_invitacion: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    codigo_expira: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    miembros: Mapped[list[User]] = relationship(back_populates="grupo")

    def __repr__(self) -> str:
        return f"<Grupo id={self.id} nombre={self.nombre!r}>"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    numero_whatsapp: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos.id"), nullable=True, index=True)

    grupo: Mapped[Grupo | None] = relationship(back_populates="miembros")
    movimientos: Mapped[list[Movimiento]] = relationship(back_populates="user")
    presupuestos: Mapped[list[Presupuesto]] = relationship(back_populates="user")
    compras_cuotas: Mapped[list[CompraCuotas]] = relationship(back_populates="user")
    deudas: Mapped[list[Deuda]] = relationship(back_populates="user")
    gastos_fijos: Mapped[list[GastoFijo]] = relationship(back_populates="user")
    tarjetas: Mapped[list[TarjetaCredito]] = relationship(back_populates="user")
    ingresos: Mapped[list[IngresoRecurrente]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} nombre={self.nombre!r}>"


class Categoria(Base):
    __tablename__ = "categorias"
    __table_args__ = (
        CheckConstraint("tipo IN ('gasto', 'ingreso')", name="ck_categorias_tipo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False, default="gasto")
    es_fijo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    movimientos: Mapped[list[Movimiento]] = relationship(back_populates="categoria")
    presupuestos: Mapped[list[Presupuesto]] = relationship(back_populates="categoria")
    gastos_fijos: Mapped[list[GastoFijo]] = relationship(back_populates="categoria")

    def __repr__(self) -> str:
        return f"<Categoria id={self.id} nombre={self.nombre!r} tipo={self.tipo!r}>"


class Movimiento(Base):
    __tablename__ = "movimientos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias.id"),
        nullable=True,
        index=True,
    )
    monto_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    mensaje_original: Mapped[str] = mapped_column(Text, nullable=False)
    fue_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confianza_parsing: Mapped[float | None] = mapped_column(Float, nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    fecha_gasto: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    es_compartido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    porcentaje_compartido: Mapped[int | None] = mapped_column(Integer, nullable=True)
    medio_pago: Mapped[str | None] = mapped_column(Text, nullable=True)
    compra_cuotas_id: Mapped[int | None] = mapped_column(
        ForeignKey("compras_cuotas.id"),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="movimientos")
    categoria: Mapped[Categoria | None] = relationship(back_populates="movimientos")
    compra_cuotas: Mapped[CompraCuotas | None] = relationship(back_populates="pagos")

    @property
    def eliminado(self) -> bool:
        return self.eliminado_en is not None

    def __repr__(self) -> str:
        return f"<Movimiento id={self.id} monto_cop={self.monto_cop}>"


class TarjetaCredito(Base):
    __tablename__ = "tarjetas_credito"
    __table_args__ = (
        UniqueConstraint("user_id", "nombre", name="uq_tarjeta_user_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    banco: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    ultimos_4: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_corte: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_pago: Mapped[int] = mapped_column(Integer, nullable=False)
    tasa_ea: Mapped[float | None] = mapped_column(Float, nullable=True)
    cupo_total_cop: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped[User] = relationship(back_populates="tarjetas")
    compras: Mapped[list[CompraCuotas]] = relationship(back_populates="tarjeta_rel")

    def __repr__(self) -> str:
        return f"<TarjetaCredito id={self.id} nombre={self.nombre!r} banco={self.banco!r}>"


class CompraCuotas(Base):
    __tablename__ = "compras_cuotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    tarjeta_id: Mapped[int | None] = mapped_column(
        ForeignKey("tarjetas_credito.id"), nullable=True, index=True,
    )
    fecha_compra: Mapped[date] = mapped_column(Date, nullable=False)
    establecimiento: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_total_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    num_cuotas: Mapped[int] = mapped_column(Integer, nullable=False)
    cuotas_pagadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valor_cuota_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_intereses_cop: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasa_ea: Mapped[float | None] = mapped_column(Float, nullable=True)
    numero_transaccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tarjeta: Mapped[str | None] = mapped_column(Text, nullable=True)
    saldo_pendiente_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    liquidada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_ultima_cuota: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_primera_cuota: Mapped[date | None] = mapped_column(Date, nullable=True)
    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    user: Mapped[User] = relationship(back_populates="compras_cuotas")
    tarjeta_rel: Mapped[TarjetaCredito | None] = relationship(back_populates="compras")
    pagos: Mapped[list[Movimiento]] = relationship(back_populates="compra_cuotas")

    @property
    def cuotas_restantes(self) -> int:
        return self.num_cuotas - self.cuotas_pagadas

    def __repr__(self) -> str:
        return (
            f"<CompraCuotas id={self.id} {self.establecimiento!r} "
            f"{self.cuotas_pagadas}/{self.num_cuotas}>"
        )


class Deuda(Base):
    __tablename__ = "deudas"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('personal', 'tarjeta', 'credito')",
            name="ck_deudas_tipo",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False, default="personal")
    acreedor: Mapped[str | None] = mapped_column(Text, nullable=True)
    monto_original_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    saldo_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    cuota_mensual_cop: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tasa_ea: Mapped[float | None] = mapped_column(Float, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="deudas")

    def __repr__(self) -> str:
        return f"<Deuda id={self.id} nombre={self.nombre!r} saldo={self.saldo_cop}>"


class GastoFijo(Base):
    __tablename__ = "gastos_fijos"
    __table_args__ = (
        UniqueConstraint("user_id", "nombre", name="uq_gasto_fijo_user_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    monto_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    es_compartido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    porcentaje_compartido: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dia_esperado: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="gastos_fijos")
    categoria: Mapped[Categoria] = relationship(back_populates="gastos_fijos")

    def __repr__(self) -> str:
        return f"<GastoFijo id={self.id} nombre={self.nombre!r} monto={self.monto_cop}>"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tabla: Mapped[str] = mapped_column(Text, nullable=False)
    registro_id: Mapped[int] = mapped_column(Integer, nullable=False)
    accion: Mapped[str] = mapped_column(Text, nullable=False)
    valores_anteriores: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    valores_nuevos: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    origen: Mapped[str] = mapped_column(Text, nullable=False, default="admin")
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} tabla={self.tabla!r} accion={self.accion!r}>"


class Presupuesto(Base):
    __tablename__ = "presupuestos"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "categoria_id",
            "mes_vigente",
            name="uq_presupuesto_user_categoria_mes",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id"),
        nullable=False,
        index=True,
    )
    monto_limite_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    mes_vigente: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[User] = relationship(back_populates="presupuestos")
    categoria: Mapped[Categoria] = relationship(back_populates="presupuestos")

    def __repr__(self) -> str:
        return (
            f"<Presupuesto id={self.id} mes={self.mes_vigente!r} "
            f"limite={self.monto_limite_cop}>"
        )


class IngresoRecurrente(Base):
    __tablename__ = "ingresos_recurrentes"
    __table_args__ = (
        UniqueConstraint("user_id", "nombre", name="uq_ingreso_user_nombre"),
        CheckConstraint("tipo IN ('fijo', 'variable')", name="ck_ingreso_tipo"),
        CheckConstraint(
            "frecuencia IN ('mensual', 'quincenal', 'semanal', 'anual')",
            name="ck_ingreso_frecuencia",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False, default="fijo")
    frecuencia: Mapped[str] = mapped_column(Text, nullable=False, default="mensual")
    monto_cop: Mapped[int] = mapped_column(Integer, nullable=False)
    dia_pago_1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dia_pago_2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped[User] = relationship(back_populates="ingresos")

    def __repr__(self) -> str:
        return f"<IngresoRecurrente id={self.id} nombre={self.nombre!r} tipo={self.tipo!r}>"
