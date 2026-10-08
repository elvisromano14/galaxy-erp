import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
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


class CuentaPorCobrar(Base):
    __tablename__ = "cuenta_por_cobrar"

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
    factura_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factura_venta.id", ondelete="CASCADE"),
        nullable=False,
    )
    monto_total_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monto_total_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    saldo_pendiente_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    saldo_pendiente_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDIENTE"
    )  # PENDIENTE | PARCIAL | PAGADA

    __table_args__ = (UniqueConstraint("company_id", "factura_id", name="uq_cxc_company_factura"),)


class CobroCliente(Base):
    __tablename__ = "cobro_cliente"

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
    cxc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cuenta_por_cobrar.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero_recibo: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto_cobrado_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    monto_cobrado_ves: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    retencion_iva_deducida: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    retencion_islr_deducida: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    instrumento_pago_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instrumento_pago.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cuenta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cuenta_bancaria.id", ondelete="SET NULL"),
        nullable=True,
    )
    referencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CuentaPorPagar(Base):
    __tablename__ = "cuenta_por_pagar"

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
    proveedor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proveedor.id", ondelete="RESTRICT"),
        nullable=False,
    )
    compra_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compra_factura.id", ondelete="CASCADE"),
        nullable=False,
    )
    monto_total_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monto_total_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    saldo_pendiente_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    saldo_pendiente_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDIENTE"
    )  # PENDIENTE | PARCIAL | PAGADA

    __table_args__ = (UniqueConstraint("company_id", "compra_id", name="uq_cxp_company_compra"),)


class PagoProveedor(Base):
    __tablename__ = "pago_proveedor"

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
    proveedor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proveedor.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cxp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cuenta_por_pagar.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero_comprobante: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto_pagado_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    monto_pagado_ves: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    retencion_iva_aplicada: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    retencion_islr_aplicada: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    instrumento_pago_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instrumento_pago.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cuenta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cuenta_bancaria.id", ondelete="SET NULL"),
        nullable=True,
    )
    referencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
