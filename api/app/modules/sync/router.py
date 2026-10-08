"""Router de FastAPI para el protocolo de sincronización offline."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import TokenData
from app.modules.sync.schemas import (
    BatchOperacionesSyncRequest,
    BatchOperacionesSyncResponse,
    BloqueCorrelativoRequest,
    BloqueCorrelativoResponse,
    CatalogosSyncResponse,
    DispositivoSyncCreate,
    DispositivoSyncResponse,
)
from app.modules.sync.service import SyncService
from app.tenancy.deps import get_token_auth, sesion_tenant

router = APIRouter(prefix="/api/v1/sync", tags=["Sincronización Offline y Preventa"])


@router.post("/dispositivos", response_model=DispositivoSyncResponse, status_code=201)
async def registrar_dispositivo(
    data: DispositivoSyncCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await SyncService.registrar_dispositivo(session, token.cid, data)


@router.get("/catalogos", response_model=CatalogosSyncResponse)
async def descargar_catalogos(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
    desde: Annotated[int, Query(ge=0)] = 0,
) -> Any:
    return await SyncService.descargar_catalogos(session, token.cid, desde)


@router.post("/bloques", response_model=BloqueCorrelativoResponse, status_code=201)
async def solicitar_bloque_correlativo(
    data: BloqueCorrelativoRequest,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await SyncService.solicitar_bloque(session, token.cid, data)


@router.post("/operaciones", response_model=BatchOperacionesSyncResponse)
async def procesar_operaciones_offline(
    data: BatchOperacionesSyncRequest,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await SyncService.procesar_operaciones(session, token.cid, token.uid, data)
