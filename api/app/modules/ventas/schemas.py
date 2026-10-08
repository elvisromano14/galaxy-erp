import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VentaItem(BaseModel):
    product_id: uuid.UUID
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)
    precio_unitario: Decimal = Field(..., gt=0, decimal_places=4)
    alicuota_iva: Decimal = Field(default=Decimal("16.00"), ge=0, le=100)


class PresupuestoVentaCreate(BaseModel):
    cliente_id: uuid.UUID
    warehouse_id: uuid.UUID
    vendedor_id: uuid.UUID | None = None
    fecha: date
    vigencia_dias: int = Field(default=15, ge=1)
    moneda: str = Field(default="USD", max_length=3)
    notas: str | None = None
    items: list[VentaItem] = Field(..., min_length=1)


class PresupuestoVentaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    cliente_id: uuid.UUID
    numero: str
    fecha: date
    tasa_cambio: Decimal
    moneda: str
    total_usd: Decimal
    total_ves: Decimal
    estado: str
    created_at: datetime


class FacturaVentaCreate(BaseModel):
    cliente_id: uuid.UUID
    warehouse_id: uuid.UUID
    vendedor_id: uuid.UUID | None = None
    presupuesto_id: uuid.UUID | None = None
    fecha_emision: date
    moneda: str = Field(default="USD", max_length=3)
    tasa_cambio: Decimal | None = Field(
        default=None, gt=0, description="Opcional: si se omite se usa tasa del día"
    )
    items: list[VentaItem] = Field(..., min_length=1)


class FacturaVentaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    cliente_id: uuid.UUID
    warehouse_id: uuid.UUID
    vendedor_id: uuid.UUID | None
    numero_factura: str
    numero_control: str
    fecha_emision: date
    tasa_cambio: Decimal
    moneda: str
    monto_exento: Decimal
    base_imponible: Decimal
    monto_iva: Decimal
    total_usd: Decimal
    total_ves: Decimal
    cliente_retiene_iva: bool
    porcentaje_retencion_iva: Decimal
    monto_retencion_iva: Decimal
    cliente_retiene_islr: bool
    porcentaje_retencion_islr: Decimal
    monto_retencion_islr: Decimal
    saldo_pendiente_usd: Decimal
    saldo_pendiente_ves: Decimal
    estado: str
    created_at: datetime


class NotaCreditoCreate(BaseModel):
    factura_id: uuid.UUID
    fecha_emision: date
    motivo: str = Field(..., min_length=5)
    monto_total_usd: Decimal = Field(..., gt=0)
    monto_total_ves: Decimal = Field(..., gt=0)
