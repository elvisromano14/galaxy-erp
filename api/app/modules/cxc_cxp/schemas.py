import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CuentaPorCobrarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    cliente_id: uuid.UUID
    factura_id: uuid.UUID
    monto_total_usd: Decimal
    monto_total_ves: Decimal
    saldo_pendiente_usd: Decimal
    saldo_pendiente_ves: Decimal
    fecha_emision: date
    fecha_vencimiento: date
    estado: str


class CobroClienteCreate(BaseModel):
    cxc_id: uuid.UUID
    fecha: date
    monto_cobrado_usd: Decimal = Field(default=Decimal("0.00"), ge=0)
    monto_cobrado_ves: Decimal = Field(default=Decimal("0.00"), ge=0)
    retencion_iva_deducida: Decimal = Field(default=Decimal("0.00"), ge=0)
    retencion_islr_deducida: Decimal = Field(default=Decimal("0.00"), ge=0)
    instrumento_pago_id: uuid.UUID
    cuenta_bancaria_id: uuid.UUID | None = None
    referencia: str | None = None
    notas: str | None = None


class CobroClienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    cliente_id: uuid.UUID
    cxc_id: uuid.UUID
    numero_recibo: str
    fecha: date
    monto_cobrado_usd: Decimal
    monto_cobrado_ves: Decimal
    retencion_iva_deducida: Decimal
    retencion_islr_deducida: Decimal
    created_at: datetime


class CuentaPorPagarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    proveedor_id: uuid.UUID
    compra_id: uuid.UUID
    monto_total_usd: Decimal
    monto_total_ves: Decimal
    saldo_pendiente_usd: Decimal
    saldo_pendiente_ves: Decimal
    fecha_emision: date
    fecha_vencimiento: date
    estado: str


class PagoProveedorCreate(BaseModel):
    cxp_id: uuid.UUID
    fecha: date
    monto_pagado_usd: Decimal = Field(default=Decimal("0.00"), ge=0)
    monto_pagado_ves: Decimal = Field(default=Decimal("0.00"), ge=0)
    retencion_iva_aplicada: Decimal = Field(default=Decimal("0.00"), ge=0)
    retencion_islr_aplicada: Decimal = Field(default=Decimal("0.00"), ge=0)
    instrumento_pago_id: uuid.UUID
    cuenta_bancaria_id: uuid.UUID | None = None
    referencia: str | None = None
    notas: str | None = None


class PagoProveedorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    proveedor_id: uuid.UUID
    cxp_id: uuid.UUID
    numero_comprobante: str
    fecha: date
    monto_pagado_usd: Decimal
    monto_pagado_ves: Decimal
    retencion_iva_aplicada: Decimal
    retencion_islr_aplicada: Decimal
    created_at: datetime


class AntiguedadBucket(BaseModel):
    dias_0_30: Decimal = Decimal("0.00")
    dias_31_60: Decimal = Decimal("0.00")
    dias_61_90: Decimal = Decimal("0.00")
    dias_mas_90: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
