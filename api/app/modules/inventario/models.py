import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class StockBalance(Base):
    __tablename__ = "stock_balance"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.id", ondelete="CASCADE"),
        primary_key=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )

    __table_args__ = (CheckConstraint("cantidad >= 0", name="chk_stock_balance_cantidad_positiva"),)


class StockMovement(Base):
    """Kardex inmutable y append-only (auditoría obligatoria de movimientos de inventario)."""

    __tablename__ = "stock_movement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # COMPRA | VENTA | TRASLADO_IN | TRASLADO_OUT | AJUSTE_POS | AJUSTE_NEG | CARGO | DESCARGO
    documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    documento_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False
    )  # Positivo para entrada, negativo para salida
    costo_std: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )


class AjusteInventario(Base):
    __tablename__ = "ajuste_inventario"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="RESTRICT"),
        nullable=False,
    )
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)  # Motivo obligatorio
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="BORRADOR"
    )  # BORRADOR | APROBADO | ANULADO
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("company_id", "numero", name="uq_ajuste_inventario_company_numero"),
    )


class AjusteInventarioDetalle(Base):
    __tablename__ = "ajuste_inventario_detalle"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    ajuste_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ajuste_inventario.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad_sistema: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cantidad_fisica: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    diferencia: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)


class TrasladoInventario(Base):
    __tablename__ = "traslado_inventario"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    origen_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="RESTRICT"),
        nullable=False,
    )
    destino_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="RESTRICT"),
        nullable=False,
    )
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="COMPLETADO"
    )  # COMPLETADO | ANULADO
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("company_id", "numero", name="uq_traslado_inventario_company_numero"),
    )


class TrasladoInventarioDetalle(Base):
    __tablename__ = "traslado_inventario_detalle"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    traslado_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traslado_inventario.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
