import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import TokenData
from app.modules.inventario.schemas import (
    AjusteCreate,
    MovimientoManualCreate,
    StockBalanceResponse,
    StockMovementResponse,
    TrasladoCreate,
)
from app.modules.inventario.service import InventarioService
from app.tenancy.deps import get_token_auth, sesion_tenant

router = APIRouter(prefix="/api/v1/inventario", tags=["Inventario y Almacenes"])


@router.get("/saldos", response_model=list[StockBalanceResponse])
async def listar_saldos(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
    warehouse_id: uuid.UUID | None = None,
) -> Any:
    return await InventarioService.listar_saldos(session, token.cid, warehouse_id)


@router.get("/kardex", response_model=list[StockMovementResponse])
async def listar_kardex(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
) -> Any:
    return await InventarioService.listar_kardex(session, token.cid, product_id, warehouse_id)


@router.post("/movimientos-manuales", response_model=StockMovementResponse, status_code=201)
async def registrar_movimiento_manual(
    data: MovimientoManualCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await InventarioService.aplicar_movimiento_manual(session, token.cid, token.uid, data)


@router.post("/traslados", status_code=201)
async def ejecutar_traslado(
    data: TrasladoCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> dict[str, Any]:
    traslado = await InventarioService.ejecutar_traslado(session, token.cid, token.uid, data)
    return {"id": traslado.id, "numero": traslado.numero, "estado": traslado.estado}


@router.post("/ajustes", status_code=201)
async def ejecutar_ajuste(
    data: AjusteCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> dict[str, Any]:
    ajuste = await InventarioService.ejecutar_ajuste(session, token.cid, token.uid, data)
    return {"id": ajuste.id, "numero": ajuste.numero, "estado": ajuste.estado}


@router.get("/verificar-invariante")
async def verificar_invariante(
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> dict[str, Any]:
    es_valido = await InventarioService.verificar_invariante_kardex(
        session, token.cid, warehouse_id, product_id
    )
    return {
        "warehouse_id": warehouse_id,
        "product_id": product_id,
        "invariante_valida": es_valido,
    }
