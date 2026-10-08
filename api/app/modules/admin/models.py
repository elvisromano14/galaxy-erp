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
    direccion_fiscal: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agente_retencion_iva: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    porcentaje_retencion_iva_default: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("75.00")
    )
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


class TasaCambio(Base):
    __tablename__ = "tasa_cambio"

    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    moneda: Mapped[str] = mapped_column(String(3), primary_key=True, default="USD")
    fuente: Mapped[str] = mapped_column(String(20), primary_key=True, default="BCV")  # BCV | MANUAL
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Categoria(Base):
    __tablename__ = "categoria"

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
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categoria.id", ondelete="SET NULL"),
        nullable=True,
    )
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("company_id", "codigo", name="uq_categoria_company_codigo"),)


class Product(Base):
    __tablename__ = "product"

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
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categoria.id", ondelete="RESTRICT"),
        nullable=False,
    )
    alicuota_iva_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alicuota_iva.id", ondelete="RESTRICT"),
        nullable=False,
    )
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    codigo_barras: Mapped[str | None] = mapped_column(String(40), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    unidad: Mapped[str] = mapped_column(String(10), nullable=False, default="UND")
    costo_estandar: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    precio_base_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    minimo: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    maximo: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (UniqueConstraint("company_id", "codigo", name="uq_product_company_codigo"),)


class Proveedor(Base):
    __tablename__ = "proveedor"

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
    rif: Mapped[str] = mapped_column(String(20), nullable=False)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contribuyente: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ORDINARIO"
    )  # ORDINARIO | ESPECIAL
    retiene_iva: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # Configurable por proveedor
    porcentaje_retencion_iva: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("75.00")
    )
    retiene_islr: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Configurable por proveedor
    porcentaje_retencion_islr: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    dias_credito: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (UniqueConstraint("company_id", "rif", name="uq_proveedor_company_rif"),)


class Zona(Base):
    __tablename__ = "zona"

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
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("company_id", "codigo", name="uq_zona_company_codigo"),)


class Vendedor(Base):
    __tablename__ = "vendedor"

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
    zona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zona.id", ondelete="SET NULL"),
        nullable=True,
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
    )
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comision_porcentaje: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("company_id", "codigo", name="uq_vendedor_company_codigo"),)


class Cliente(Base):
    __tablename__ = "cliente"

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
    tipo_identificacion: Mapped[str] = mapped_column(
        String(2), nullable=False, default="V"
    )  # V | J | E | G | P
    identificacion: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contribuyente: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ORDINARIO"
    )  # ORDINARIO | ESPECIAL
    nos_retiene_iva: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Configurable: True si este cliente nos retiene IVA
    porcentaje_retencion_iva: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("75.00")
    )
    nos_retiene_islr: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Configurable: True si este cliente nos retiene ISLR
    porcentaje_retencion_islr: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    zona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zona.id", ondelete="SET NULL"),
        nullable=True,
    )
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendedor.id", ondelete="SET NULL"),
        nullable=True,
    )
    limite_credito: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    dias_credito: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("company_id", "identificacion", name="uq_cliente_company_identificacion"),
    )


class InstrumentoPago(Base):
    __tablename__ = "instrumento_pago"

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
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # EFECTIVO | TRANSFERENCIA | PAGO_MOVIL | PUNTO_VENTA | ZELLE | OTRO
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="VES")  # VES | USD
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_instrumento_pago_company_codigo"),
    )


class TipoOperacion(Base):
    __tablename__ = "tipo_operacion"

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
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    modulo: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # INVENTARIO | VENTAS | COMPRAS | FINANZAS
    afecta_inventario: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signo_inventario: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # +1 (entrada), -1 (salida), 0 (neutral)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_tipo_operacion_company_codigo"),
    )


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
