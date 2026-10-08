import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import TokenData
from app.core.tiempo import hoy_ccs
from app.modules.admin.bcv import sincronizar_tasa_bcv
from app.modules.admin.importador import importar_productos_excel
from app.modules.admin.schemas import (
    CategoriaCreate,
    CategoriaResponse,
    ClienteCreate,
    ClienteResponse,
    InstrumentoPagoCreate,
    InstrumentoPagoResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ProveedorCreate,
    ProveedorResponse,
    TasaCambioCreate,
    TasaCambioResponse,
    TipoOperacionCreate,
    TipoOperacionResponse,
    VendedorCreate,
    VendedorResponse,
    WarehouseCreate,
    WarehouseResponse,
    ZonaCreate,
    ZonaResponse,
)
from app.modules.admin.service import AdminService
from app.tenancy.deps import get_token_auth, sesion_tenant

router = APIRouter(prefix="/api/v1/admin", tags=["Administración y Catálogos"])


# --- TASAS DE CAMBIO ---
@router.post("/tasas", response_model=TasaCambioResponse, status_code=201)
async def registrar_tasa(
    data: TasaCambioCreate,
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.registrar_tasa(session, data)


@router.get("/tasas/actual")
async def obtener_tasa_actual(
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
    fecha: date | None = None,
    moneda: str = "USD",
) -> dict[str, Any]:
    fecha_ref = fecha or hoy_ccs()
    valor = await AdminService.obtener_tasa_actual(session, fecha_ref, moneda)
    return {"fecha": fecha_ref, "moneda": moneda, "valor": valor}


@router.post("/tasas/sincronizar-bcv", status_code=200)
async def sincronizar_bcv(
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> dict[str, Any]:
    tasa = await sincronizar_tasa_bcv(session)
    if tasa:
        return {"mensaje": "Tasa sincronizada con BCV", "valor": tasa.valor, "fecha": tasa.fecha}
    return {"mensaje": "No se pudo sincronizar o ya existía tasa para la fecha."}


# --- CATEGORIAS ---
@router.post("/categorias", response_model=CategoriaResponse, status_code=201)
async def crear_categoria(
    data: CategoriaCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_categoria(session, token.cid, data)


@router.get("/categorias", response_model=list[CategoriaResponse])
async def listar_categorias(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.listar_categorias(session, token.cid)


# --- PRODUCTOS ---
@router.post("/productos", response_model=ProductResponse, status_code=201)
async def crear_producto(
    data: ProductCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_producto(session, token.cid, data)


@router.get("/productos", response_model=list[ProductResponse])
async def listar_productos(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
    categoria_id: uuid.UUID | None = None,
) -> Any:
    return await AdminService.listar_productos(session, token.cid, categoria_id)


@router.patch("/productos/{producto_id}", response_model=ProductResponse)
async def actualizar_producto(
    producto_id: uuid.UUID,
    data: ProductUpdate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.actualizar_producto(session, token.cid, producto_id, data)


@router.post("/productos/importar-excel")
async def importar_productos(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
    archivo: UploadFile = File(...),
) -> dict[str, Any]:
    contenido = await archivo.read()
    return await importar_productos_excel(session, token.cid, contenido)


# --- PROVEEDORES (Retenciones configurables) ---
@router.post("/proveedores", response_model=ProveedorResponse, status_code=201)
async def crear_proveedor(
    data: ProveedorCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_proveedor(session, token.cid, data)


@router.get("/proveedores", response_model=list[ProveedorResponse])
async def listar_proveedores(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.listar_proveedores(session, token.cid)


# --- CLIENTES (Retenciones configurables) ---
@router.post("/clientes", response_model=ClienteResponse, status_code=201)
async def crear_cliente(
    data: ClienteCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_cliente(session, token.cid, data)


@router.get("/clientes", response_model=list[ClienteResponse])
async def listar_clientes(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.listar_clientes(session, token.cid)


# --- ZONAS Y VENDEDORES ---
@router.post("/zonas", response_model=ZonaResponse, status_code=201)
async def crear_zona(
    data: ZonaCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_zona(session, token.cid, data)


@router.get("/zonas", response_model=list[ZonaResponse])
async def listar_zonas(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.listar_zonas(session, token.cid)


@router.post("/vendedores", response_model=VendedorResponse, status_code=201)
async def crear_vendedor(
    data: VendedorCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_vendedor(session, token.cid, data)


@router.get("/vendedores", response_model=list[VendedorResponse])
async def listar_vendedores(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.listar_vendedores(session, token.cid)


# --- INSTRUMENTOS DE PAGO Y OPERACION ---
@router.post("/instrumentos-pago", response_model=InstrumentoPagoResponse, status_code=201)
async def crear_instrumento_pago(
    data: InstrumentoPagoCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_instrumento_pago(session, token.cid, data)


@router.get("/instrumentos-pago", response_model=list[InstrumentoPagoResponse])
async def listar_instrumentos_pago(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.listar_instrumentos_pago(session, token.cid)


@router.post("/tipos-operacion", response_model=TipoOperacionResponse, status_code=201)
async def crear_tipo_operacion(
    data: TipoOperacionCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_tipo_operacion(session, token.cid, data)


@router.get("/tipos-operacion", response_model=list[TipoOperacionResponse])
async def listar_tipos_operacion(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.listar_tipos_operacion(session, token.cid)


# --- ALMACENES ---
@router.post("/almacenes", response_model=WarehouseResponse, status_code=201)
async def crear_almacen(
    data: WarehouseCreate,
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.crear_almacen(session, token.cid, data)


@router.get("/almacenes", response_model=list[WarehouseResponse])
async def listar_almacenes(
    token: Annotated[TokenData, Depends(get_token_auth)],
    session: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> Any:
    return await AdminService.listar_almacenes(session, token.cid)
