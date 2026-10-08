import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompraItem(BaseModel):
    product_id: uuid.UUID
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)
    costo_unitario: Decimal = Field(..., gt=0, decimal_places=4)
    alicuota_iva: Decimal = Field(default=Decimal("16.00"), ge=0, le=100)


class CompraFacturaCreate(BaseModel):
    proveedor_id: uuid.UUID
    warehouse_id: uuid.UUID
    numero_factura: str = Field(..., min_length=1, max_length=30)
    numero_control: str | None = None
    fecha_emision: date
    moneda: str = Field(default="USD", max_length=3)
    tasa_cambio: Decimal | None = Field(
        default=None, gt=0, description="Opcional: si se omite, se usa la tasa del día"
    )
    items: list[CompraItem] = Field(..., min_length=1)


class CompraFacturaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    proveedor_id: uuid.UUID
    warehouse_id: uuid.UUID
    numero_factura: str
    numero_control: str | None
    fecha_emision: date
    tasa_cambio: Decimal
    moneda: str
    base_imponible: Decimal
    monto_exento: Decimal
    monto_iva: Decimal
    total_usd: Decimal
    total_ves: Decimal
    aplica_retencion_iva: bool
    porcentaje_retencion_iva: Decimal
    monto_retencion_iva: Decimal
    aplica_retencion_islr: bool
    porcentaje_retencion_islr: Decimal
    monto_retencion_islr: Decimal
    estado: str
    created_at: datetime
