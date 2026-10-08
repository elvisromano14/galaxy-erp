import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CuentaBancariaCreate(BaseModel):
    banco_nombre: str = Field(..., min_length=2, max_length=100)
    numero_cuenta: str = Field(..., min_length=5, max_length=50)
    tipo: str = Field(default="CORRIENTE", max_length=20)
    moneda: str = Field(default="VES", max_length=3)
    saldo_inicial: Decimal = Field(default=Decimal("0.00"), ge=0)


class CuentaBancariaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    banco_nombre: str
    numero_cuenta: str
    tipo: str
    moneda: str
    saldo_actual: Decimal
    activa: bool


class TransaccionBancariaCreate(BaseModel):
    cuenta_id: uuid.UUID
    fecha: date
    tipo: str = Field(..., description="INGRESO o EGRESO")
    referencia: str = Field(..., min_length=1, max_length=50)
    monto: Decimal = Field(..., gt=0, decimal_places=2)
    tasa_cambio: Decimal = Field(default=Decimal("1.000000"), gt=0)
    descripcion: str = Field(..., min_length=3)


class TransaccionBancariaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    cuenta_id: uuid.UUID
    fecha: date
    tipo: str
    referencia: str
    monto: Decimal
    tasa_cambio: Decimal
    descripcion: str
    conciliado: bool
    created_at: datetime
