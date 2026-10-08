from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import TokenData
from app.modules.ventas.schemas import (
    FacturaVentaCreate,
    FacturaVentaResponse,
    NotaCreditoCreate,
    PresupuestoVentaCreate,
    PresupuestoVentaResponse,
)
from app.modules.ventas.service import VentasService
from app.tenancy.deps import get_token_auth, sesion_tenant

router = APIRouter(prefix="/api/v1/ventas", tags=["Ventas y Facturación"])


@router.post("/presupuestos", response_model=PresupuestoVentaResponse, status_code=201)
async def crear_presupuesto(
    data: PresupuestoVentaCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await VentasService.crear_presupuesto(session, token.cid, token.uid, data)


@router.post("/facturas", response_model=FacturaVentaResponse, status_code=201)
async def emitir_factura(
    data: FacturaVentaCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await VentasService.emitir_factura(session, token.cid, token.uid, data)


@router.get("/facturas", response_model=list[FacturaVentaResponse])
async def listar_facturas(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await VentasService.listar_facturas(session, token.cid)


@router.post("/notas-credito", status_code=201)
async def crear_nota_credito(
    data: NotaCreditoCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> dict[str, Any]:
    nc = await VentasService.crear_nota_credito(session, token.cid, token.uid, data)
    return {"id": nc.id, "numero_nota": nc.numero_nota, "numero_control": nc.numero_control}


@router.get("/facturas/{factura_id}/pdf")
async def descargar_factura_pdf(
    factura_id: Any,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    from fastapi import Response

    pdf_bytes = await VentasService.obtener_factura_pdf(session, token.cid, factura_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=factura_{factura_id}.pdf"},
    )
