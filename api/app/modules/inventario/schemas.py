import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StockBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    cantidad: Decimal


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    tipo: str
    documento_id: uuid.UUID
    documento_tipo: str
    cantidad: Decimal
    costo_std: Decimal
    motivo: str | None
    fecha: datetime


class MovimientoManualCreate(BaseModel):
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    tipo: str = Field(..., description="CARGO o DESCARGO")
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)
    costo_std: Decimal = Field(default=Decimal("0.0000"), ge=0, decimal_places=4)
    motivo: str = Field(..., min_length=3, description="Justificación obligatoria")


class TrasladoItem(BaseModel):
    product_id: uuid.UUID
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)


class TrasladoCreate(BaseModel):
    origen_warehouse_id: uuid.UUID
    destino_warehouse_id: uuid.UUID
    motivo: str | None = None
    items: list[TrasladoItem] = Field(..., min_length=1)


class AjusteItem(BaseModel):
    product_id: uuid.UUID
    cantidad_fisica: Decimal = Field(..., ge=0, decimal_places=4)
    costo_unitario: Decimal = Field(default=Decimal("0.0000"), ge=0, decimal_places=4)


class AjusteCreate(BaseModel):
    warehouse_id: uuid.UUID
    motivo: str = Field(..., min_length=5, description="Motivo obligatorio del ajuste")
    items: list[AjusteItem] = Field(..., min_length=1)
