import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# --- TASAS DE CAMBIO ---
class TasaCambioCreate(BaseModel):
    fecha: date
    moneda: str = Field(default="USD", max_length=3)
    fuente: str = Field(default="MANUAL", max_length=20)
    valor: Decimal = Field(..., gt=0, decimal_places=6)


class TasaCambioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: date
    moneda: str
    fuente: str
    valor: Decimal
    created_at: datetime


# --- CATEGORIAS ---
class CategoriaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=30)
    nombre: str = Field(..., min_length=1, max_length=120)
    descripcion: str | None = None
    parent_id: uuid.UUID | None = None


class CategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    parent_id: uuid.UUID | None
    codigo: str
    nombre: str
    descripcion: str | None
    activo: bool


# --- PRODUCTOS ---
class ProductCreate(BaseModel):
    categoria_id: uuid.UUID
    alicuota_iva_id: uuid.UUID
    codigo: str = Field(..., min_length=1, max_length=40)
    codigo_barras: str | None = None
    descripcion: str = Field(..., min_length=1, max_length=200)
    unidad: str = Field(default="UND", max_length=10)
    costo_estandar: Decimal = Field(default=Decimal("0.0000"), ge=0, decimal_places=4)
    precio_base_usd: Decimal = Field(default=Decimal("0.0000"), ge=0, decimal_places=4)
    minimo: Decimal = Field(default=Decimal("0.0000"), ge=0, decimal_places=4)
    maximo: Decimal = Field(default=Decimal("0.0000"), ge=0, decimal_places=4)


class ProductUpdate(BaseModel):
    categoria_id: uuid.UUID | None = None
    alicuota_iva_id: uuid.UUID | None = None
    descripcion: str | None = None
    unidad: str | None = None
    costo_estandar: Decimal | None = None
    precio_base_usd: Decimal | None = None
    minimo: Decimal | None = None
    maximo: Decimal | None = None
    activo: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    categoria_id: uuid.UUID
    alicuota_iva_id: uuid.UUID
    codigo: str
    codigo_barras: str | None
    descripcion: str
    unidad: str
    costo_estandar: Decimal
    precio_base_usd: Decimal
    minimo: Decimal
    maximo: Decimal
    activo: bool
    version: int
    created_at: datetime
    updated_at: datetime


# --- PROVEEDORES ---
class ProveedorCreate(BaseModel):
    rif: str = Field(..., min_length=4, max_length=20)
    razon_social: str = Field(..., min_length=2, max_length=200)
    direccion: str | None = None
    telefono: str | None = None
    email: str | None = None
    contribuyente: str = Field(default="ORDINARIO", max_length=20)
    retiene_iva: bool = Field(default=True, description="Configurable por proveedor")
    porcentaje_retencion_iva: Decimal = Field(default=Decimal("75.00"), ge=0, le=100)
    retiene_islr: bool = Field(default=False, description="Configurable por proveedor")
    porcentaje_retencion_islr: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    dias_credito: int = Field(default=0, ge=0)


class ProveedorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    rif: str
    razon_social: str
    direccion: str | None
    telefono: str | None
    email: str | None
    contribuyente: str
    retiene_iva: bool
    porcentaje_retencion_iva: Decimal
    retiene_islr: bool
    porcentaje_retencion_islr: Decimal
    dias_credito: int
    activo: bool
    created_at: datetime


# --- ZONAS Y VENDEDORES ---
class ZonaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=100)


class ZonaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    codigo: str
    nombre: str
    activa: bool


class VendedorCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=120)
    zona_id: uuid.UUID | None = None
    usuario_id: uuid.UUID | None = None
    telefono: str | None = None
    email: str | None = None
    comision_porcentaje: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class VendedorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    codigo: str
    nombre: str
    zona_id: uuid.UUID | None
    usuario_id: uuid.UUID | None
    telefono: str | None
    email: str | None
    comision_porcentaje: Decimal
    activo: bool


# --- CLIENTES ---
class ClienteCreate(BaseModel):
    tipo_identificacion: str = Field(default="V", max_length=2)
    identificacion: str = Field(..., min_length=3, max_length=20)
    nombre: str = Field(..., min_length=2, max_length=200)
    direccion: str | None = None
    telefono: str | None = None
    email: str | None = None
    contribuyente: str = Field(default="ORDINARIO", max_length=20)
    nos_retiene_iva: bool = Field(default=False, description="Configurable por cliente")
    porcentaje_retencion_iva: Decimal = Field(default=Decimal("75.00"), ge=0, le=100)
    nos_retiene_islr: bool = Field(default=False, description="Configurable por cliente")
    porcentaje_retencion_islr: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    zona_id: uuid.UUID | None = None
    vendedor_id: uuid.UUID | None = None
    limite_credito: Decimal = Field(default=Decimal("0.00"), ge=0)
    dias_credito: int = Field(default=0, ge=0)


class ClienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    tipo_identificacion: str
    identificacion: str
    nombre: str
    direccion: str | None
    telefono: str | None
    email: str | None
    contribuyente: str
    nos_retiene_iva: bool
    porcentaje_retencion_iva: Decimal
    nos_retiene_islr: bool
    porcentaje_retencion_islr: Decimal
    zona_id: uuid.UUID | None
    vendedor_id: uuid.UUID | None
    limite_credito: Decimal
    dias_credito: int
    activo: bool
    created_at: datetime


# --- INSTRUMENTOS DE PAGO Y OPERACION ---
class InstrumentoPagoCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=100)
    tipo: str = Field(..., max_length=30)
    moneda: str = Field(default="VES", max_length=3)


class InstrumentoPagoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    codigo: str
    nombre: str
    tipo: str
    moneda: str
    activo: bool


class TipoOperacionCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=100)
    modulo: str = Field(..., max_length=30)
    afecta_inventario: bool = False
    signo_inventario: int = Field(default=0, ge=-1, le=1)


class TipoOperacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    codigo: str
    nombre: str
    modulo: str
    afecta_inventario: bool
    signo_inventario: int
    activo: bool


# --- ALMACENES ---
class WarehouseCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=120)


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    codigo: str
    nombre: str
    activo: bool
