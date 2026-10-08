from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import TokenData
from app.modules.compras.schemas import CompraFacturaCreate, CompraFacturaResponse
from app.modules.compras.service import ComprasService
from app.tenancy.deps import get_token_auth, sesion_tenant

router = APIRouter(prefix="/api/v1/compras", tags=["Compras y Recepciones"])


@router.post("", response_model=CompraFacturaResponse, status_code=201)
async def registrar_compra(
    data: CompraFacturaCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await ComprasService.registrar_compra(session, token.cid, token.uid, data)


@router.get("", response_model=list[CompraFacturaResponse])
async def listar_compras(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await ComprasService.listar_compras(session, token.cid)
