from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import TokenData
from app.modules.cxc_cxp.schemas import (
    AntiguedadBucket,
    CobroClienteCreate,
    CobroClienteResponse,
    CuentaPorCobrarResponse,
    CuentaPorPagarResponse,
    PagoProveedorCreate,
    PagoProveedorResponse,
)
from app.modules.cxc_cxp.service import CxcCxpService
from app.tenancy.deps import get_token_auth, sesion_tenant

router = APIRouter(prefix="/api/v1/finanzas", tags=["Cuentas por Cobrar y Pagar (Finanzas)"])


@router.get("/cxc", response_model=list[CuentaPorCobrarResponse])
async def listar_cuentas_por_cobrar(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await CxcCxpService.listar_cxc(session, token.cid)


@router.post("/cobros", response_model=CobroClienteResponse, status_code=201)
async def registrar_cobro_cliente(
    data: CobroClienteCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await CxcCxpService.aplicar_cobro(session, token.cid, data)


@router.get("/cxp", response_model=list[CuentaPorPagarResponse])
async def listar_cuentas_por_pagar(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await CxcCxpService.listar_cxp(session, token.cid)


@router.post("/pagos", response_model=PagoProveedorResponse, status_code=201)
async def registrar_pago_proveedor(
    data: PagoProveedorCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await CxcCxpService.aplicar_pago(session, token.cid, data)


@router.get("/antiguedad-cxc", response_model=AntiguedadBucket)
async def reporte_antiguedad_cxc(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
    fecha_corte: date | None = None,
) -> Any:
    return await CxcCxpService.calcular_antiguedad_cxc(session, token.cid, fecha_corte)
