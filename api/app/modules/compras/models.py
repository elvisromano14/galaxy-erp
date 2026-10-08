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


class OrdenCompra(Base):
    __tablename__ = "orden_compra"

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
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="RESTRICT"),
        nullable=False,
    )
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="BORRADOR"
    )  # BORRADOR | APROBADA | RECIBIDA | ANULADA
    total_estimado: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
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
        UniqueConstraint("company_id", "numero", name="uq_orden_compra_company_numero"),
    )


class OrdenCompraDetalle(Base):
    __tablename__ = "orden_compra_detalle"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    orden_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orden_compra.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class CompraFactura(Base):
    __tablename__ = "compra_factura"

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
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouse.id", ondelete="RESTRICT"),
        nullable=False,
    )
    orden_compra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orden_compra.id", ondelete="SET NULL"),
        nullable=True,
    )
    numero_factura: Mapped[str] = mapped_column(String(30), nullable=False)
    numero_control: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    tasa_cambio: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Montos en moneda base del documento
    monto_exento: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    base_imponible: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    monto_iva: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    total_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    total_ves: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )

    # Retenciones configurables según la ficha del proveedor
    aplica_retencion_iva: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    porcentaje_retencion_iva: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    monto_retencion_iva: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    aplica_retencion_islr: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    porcentaje_retencion_islr: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    monto_retencion_islr: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )

    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="REGISTRADA"
    )  # REGISTRADA | ANULADA
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "proveedor_id",
            "numero_factura",
            name="uq_compra_factura_proveedor_numero",
        ),
    )


class CompraFacturaDetalle(Base):
    __tablename__ = "compra_factura_detalle"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    compra_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compra_factura.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    alicuota_iva: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("16.00")
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
