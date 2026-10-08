import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import TokenData
from app.modules.bancos.schemas import (
    CuentaBancariaCreate,
    CuentaBancariaResponse,
    TransaccionBancariaCreate,
    TransaccionBancariaResponse,
)
from app.modules.bancos.service import BancosService
from app.tenancy.deps import get_token_auth, sesion_tenant

router = APIRouter(prefix="/api/v1/bancos", tags=["Bancos y Tesorería"])


@router.post("/cuentas", response_model=CuentaBancariaResponse, status_code=201)
async def crear_cuenta_bancaria(
    data: CuentaBancariaCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await BancosService.crear_cuenta(session, token.cid, data)


@router.get("/cuentas", response_model=list[CuentaBancariaResponse])
async def listar_cuentas(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await BancosService.listar_cuentas(session, token.cid)


@router.post("/transacciones", response_model=TransaccionBancariaResponse, status_code=201)
async def registrar_transaccion(
    data: TransaccionBancariaCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await BancosService.registrar_transaccion(session, token.cid, data)


@router.get("/transacciones", response_model=list[TransaccionBancariaResponse])
async def listar_transacciones(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
    cuenta_id: uuid.UUID | None = None,
) -> Any:
    return await BancosService.listar_transacciones(session, token.cid, cuenta_id)
