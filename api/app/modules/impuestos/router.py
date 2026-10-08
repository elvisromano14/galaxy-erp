from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import TokenData
from app.modules.admin.models import Company
from app.modules.impuestos.schemas import (
    ComprobanteIvaResponse,
    LibroComprasResponse,
    LibroVentasResponse,
)
from app.modules.impuestos.service import ImpuestosService
from app.modules.reportes.exportador import (
    exportar_libro_compras_excel,
    exportar_libro_ventas_excel,
)
from app.tenancy.deps import get_token_auth, sesion_tenant

router = APIRouter(prefix="/api/v1/impuestos", tags=["Impuestos y Libros Fiscales SENIAT"])


@router.get("/libro-ventas", response_model=LibroVentasResponse)
async def consultar_libro_ventas(
    anio: Annotated[int, Query(ge=2020, le=2050)],
    mes: Annotated[int, Query(ge=1, le=12)],
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await ImpuestosService.generar_libro_ventas(session, token.cid, anio, mes)


@router.get("/libro-ventas/excel")
async def descargar_libro_ventas_excel(
    anio: Annotated[int, Query(ge=2020, le=2050)],
    mes: Annotated[int, Query(ge=1, le=12)],
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Response:
    libro = await ImpuestosService.generar_libro_ventas(session, token.cid, anio, mes)
    empresa = await session.get(Company, token.cid)
    nombre_emp = empresa.razon_social if empresa else "EMPRESA"
    contenido = exportar_libro_ventas_excel(libro, nombre_emp)
    headers = {"Content-Disposition": f"attachment; filename=libro_ventas_{anio}_{mes:02d}.xlsx"}
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/libro-compras", response_model=LibroComprasResponse)
async def consultar_libro_compras(
    anio: Annotated[int, Query(ge=2020, le=2050)],
    mes: Annotated[int, Query(ge=1, le=12)],
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await ImpuestosService.generar_libro_compras(session, token.cid, anio, mes)


@router.get("/libro-compras/excel")
async def descargar_libro_compras_excel(
    anio: Annotated[int, Query(ge=2020, le=2050)],
    mes: Annotated[int, Query(ge=1, le=12)],
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Response:
    libro = await ImpuestosService.generar_libro_compras(session, token.cid, anio, mes)
    empresa = await session.get(Company, token.cid)
    nombre_emp = empresa.razon_social if empresa else "EMPRESA"
    contenido = exportar_libro_compras_excel(libro, nombre_emp)
    headers = {"Content-Disposition": f"attachment; filename=libro_compras_{anio}_{mes:02d}.xlsx"}
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/retenciones-iva", response_model=list[ComprobanteIvaResponse])
async def listar_retenciones_iva(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await ImpuestosService.listar_retenciones_iva(session, token.cid)


@router.get("/retenciones-iva/{comprobante_id}/pdf")
async def descargar_retencion_iva_pdf(
    comprobante_id: Any,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Response:
    pdf_bytes = await ImpuestosService.obtener_retencion_iva_pdf(session, token.cid, comprobante_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=retencion_iva_{comprobante_id}.pdf"},
    )
