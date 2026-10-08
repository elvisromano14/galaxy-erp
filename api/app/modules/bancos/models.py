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


class CuentaBancaria(Base):
    __tablename__ = "cuenta_bancaria"

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
    banco_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    numero_cuenta: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CORRIENTE"
    )  # CORRIENTE | AHORRO | CUSTODIA
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="VES")  # VES | USD
    saldo_actual: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("company_id", "numero_cuenta", name="uq_cuenta_bancaria_company_numero"),
    )


class TransaccionBancaria(Base):
    __tablename__ = "transaccion_bancaria"

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
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cuenta_bancaria.id", ondelete="CASCADE"),
        nullable=False,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # INGRESO | EGRESO
    referencia: Mapped[str] = mapped_column(String(50), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tasa_cambio: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("1.000000")
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    conciliado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    documento_origen_tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    documento_origen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
