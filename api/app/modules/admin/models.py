import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class Company(Base):
    __tablename__ = "company"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    rif: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    contribuyente: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ORDINARIO",
    )  # ORDINARIO | ESPECIAL
    moneda_base: Mapped[str] = mapped_column(String(3), nullable=False, default="VES")
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Warehouse(Base):
    __tablename__ = "warehouse"

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
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("company_id", "codigo", name="uq_warehouse_company_codigo"),)


class AlicuotaIva(Base):
    __tablename__ = "alicuota_iva"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fuente: Mapped[str] = mapped_column(Text, nullable=False)


class Correlativo(Base):
    __tablename__ = "correlativo"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tipo: Mapped[str] = mapped_column(String(30), primary_key=True)
    serie: Mapped[str] = mapped_column(String(10), primary_key=True, default="")
    ultimo: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    llave: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    hash_cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    respuesta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    estado_http: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
