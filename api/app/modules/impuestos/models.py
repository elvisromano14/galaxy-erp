import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class ComprobanteRetencionIva(Base):
    """Comprobante de retención de IVA según Providencia Administrativa SENIAT."""

    __tablename__ = "comprobante_retencion_iva"

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
    numero_comprobante: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # Formato AAAAMMNRRRRRRRR
    periodo_fiscal: Mapped[str] = mapped_column(String(6), nullable=False)  # AAAAMM
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    base_imponible_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monto_iva_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    porcentaje_retencion: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    monto_retenido_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "numero_comprobante", name="uq_retencion_iva_company_numero"
        ),
    )


class ComprobanteRetencionIslr(Base):
    """Comprobante de retención de ISLR para personas naturales o jurídicas."""

    __tablename__ = "comprobante_retencion_islr"

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
    numero_comprobante: Mapped[str] = mapped_column(String(20), nullable=False)
    periodo_fiscal: Mapped[str] = mapped_column(String(6), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    concepto: Mapped[str] = mapped_column(
        String(100), nullable=False, default="SERVICIOS PROFESIONALES / ADQUISICION"
    )
    base_imponible_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    porcentaje_retencion: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    monto_retenido_ves: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "numero_comprobante", name="uq_retencion_islr_company_numero"
        ),
    )
