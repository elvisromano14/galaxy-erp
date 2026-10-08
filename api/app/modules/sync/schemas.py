"""Esquemas Pydantic para el protocolo de sincronización offline."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DispositivoSyncCreate(BaseModel):
    nombre: str = Field(..., max_length=100)
    identificador_unico: str = Field(..., max_length=120)
    usuario_id: uuid.UUID


class DispositivoSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    identificador_unico: str
    usuario_id: uuid.UUID
    ultimo_token: int
    activo: bool
    created_at: datetime


class CatalogosSyncResponse(BaseModel):
    sync_token: int
    productos: list[dict[str, Any]]
    clientes: list[dict[str, Any]]
    almacenes: list[dict[str, Any]]
    existencias: list[dict[str, Any]]
    alicuotas_iva: list[dict[str, Any]]
    tasa_actual_usd: Decimal | None


class BloqueCorrelativoRequest(BaseModel):
    dispositivo_id: uuid.UUID
    tipo_documento: str = Field(default="PRESUPUESTO", max_length=30)
    serie: str = Field(default="", max_length=10)
    cantidad: int = Field(default=50, ge=1, le=500)


class BloqueCorrelativoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dispositivo_id: uuid.UUID
    tipo_documento: str
    serie: str
    desde_numero: int
    hasta_numero: int
    ultimo_usado: int


class OperacionSyncItem(BaseModel):
    client_op_id: uuid.UUID
    tipo: str = Field(..., max_length=50)  # PEDIDO_VENTA, COBRO_CLIENTE
    creado_en: datetime
    tasa_usada: Decimal | None = None
    payload: dict[str, Any]


class BatchOperacionesSyncRequest(BaseModel):
    dispositivo_id: uuid.UUID
    operaciones: list[OperacionSyncItem]


class OperacionSyncResultado(BaseModel):
    client_op_id: uuid.UUID
    estado: str  # APLICADA | RECHAZADA | DUPLICADA
    documento_id: uuid.UUID | None = None
    numero: str | None = None
    error: str | None = None


class BatchOperacionesSyncResponse(BaseModel):
    resultados: list[OperacionSyncResultado]
