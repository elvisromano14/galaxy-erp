import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
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


class PresupuestoVenta(Base):
    __tablename__ = "presupuesto_venta"

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
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cliente.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendedor.id", ondelete="SET NULL"),
        nullable=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="RESTRICT"),
        nullable=False,
    )
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_dias: Mapped[int] = mapped_column(default=15)
    tasa_cambio: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), default="USD")
    total_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    estado: Mapped[str] = mapped_column(
        String(20), default="BORRADOR"
    )  # BORRADOR | APROBADO | FACTURADO | ANULADO
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("company_id", "numero", name="uq_presupuesto_venta_company_numero"),
    )


class PresupuestoVentaDetalle(Base):
    __tablename__ = "presupuesto_venta_detalle"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    presupuesto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("presupuesto_venta.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    alicuota_iva: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("16.00"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class FacturaVenta(Base):
    """Factura legal y fiscal de venta según lineamientos SENIAT."""

    __tablename__ = "factura_venta"

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
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cliente.id", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendedor.id", ondelete="SET NULL"),
        nullable=True,
    )
    presupuesto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("presupuesto_venta.id", ondelete="SET NULL"),
        nullable=True,
    )
    numero_factura: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_control: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    tasa_cambio: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    monto_exento: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    base_imponible: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    monto_iva: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    # Retenciones configurables según la ficha del cliente
    cliente_retiene_iva: Mapped[bool] = mapped_column(Boolean, default=False)
    porcentaje_retencion_iva: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    monto_retencion_iva: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    cliente_retiene_islr: Mapped[bool] = mapped_column(Boolean, default=False)
    porcentaje_retencion_islr: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    monto_retencion_islr: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    estado: Mapped[str] = mapped_column(String(20), default="EMITIDA")  # EMITIDA | ANULADA
    saldo_pendiente_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    saldo_pendiente_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("company_id", "numero_factura", name="uq_factura_venta_company_numero"),
    )


class FacturaVentaDetalle(Base):
    __tablename__ = "factura_venta_detalle"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    factura_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factura_venta.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    alicuota_iva: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("16.00"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class NotaCreditoVenta(Base):
    __tablename__ = "nota_credito_venta"

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
    factura_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factura_venta.id", ondelete="RESTRICT"),
        nullable=False,
    )
    numero_nota: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_control: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    monto_total_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monto_total_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("company_id", "numero_nota", name="uq_nota_credito_company_numero"),
    )
