"""Importador masivo de catálogo de productos desde hojas de cálculo Excel (.xlsx)."""

import io
import uuid
from decimal import Decimal
from typing import Any

import openpyxl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import GalaxyERPException
from app.modules.admin.models import AlicuotaIva, Categoria, Product


async def importar_productos_excel(
    session: AsyncSession, company_id: uuid.UUID, archivo_bytes: bytes
) -> dict[str, Any]:
    """Lee un libro Excel y carga o actualiza productos respetando aislamiento por empresa."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(archivo_bytes), data_only=True)
    except Exception as exc:
        raise GalaxyERPException(
            code="EXCEL_INVALIDO",
            title="Archivo Excel Inválido",
            status=400,
            detail=f"No se pudo procesar el archivo Excel proporcionado: {exc}",
        ) from exc

    hoja = wb.active
    if hoja is None:
        raise GalaxyERPException(
            code="HOJA_VACIA",
            title="Hoja vacía",
            status=400,
            detail="El libro de Excel no contiene hojas de datos.",
        )

    # 1. Cargar mapeo de categorías y alícuotas de la empresa en memoria
    cat_res = await session.execute(select(Categoria).where(Categoria.company_id == company_id))
    categorias_map = {c.codigo.upper(): c.id for c in cat_res.scalars().all()}

    ali_res = await session.execute(select(AlicuotaIva))
    alicuotas_map = {a.codigo.upper(): a.id for a in ali_res.scalars().all()}

    filas = list(hoja.iter_rows(values_only=True))
    if len(filas) < 2:
        return {"total_procesados": 0, "insertados": 0, "errores": []}

    encabezados = [str(c).strip().lower() if c else "" for c in filas[0]]
    # Columnas esperadas mínimas: codigo, descripcion, categoria, alicuota, precio_usd
    idx_codigo = encabezados.index("codigo") if "codigo" in encabezados else 0
    idx_desc = encabezados.index("descripcion") if "descripcion" in encabezados else 1
    idx_cat = encabezados.index("categoria") if "categoria" in encabezados else 2
    idx_ali = encabezados.index("alicuota") if "alicuota" in encabezados else 3
    idx_precio = encabezados.index("precio_usd") if "precio_usd" in encabezados else 4

    insertados = 0
    errores: list[str] = []

    for _num_fila, fila in enumerate(filas[1:], start=2):
        if not fila or not fila[idx_codigo]:
            continue

        codigo = str(fila[idx_codigo]).strip().upper()
        descripcion = str(fila[idx_desc]).strip() if fila[idx_desc] else "Sin descripción"
        cat_cod = str(fila[idx_cat]).strip().upper() if fila[idx_cat] else "GENERAL"
        ali_cod = str(fila[idx_ali]).strip().upper() if fila[idx_ali] else "GENERAL"

        try:
            precio = (
                Decimal(str(fila[idx_precio])) if fila[idx_precio] is not None else Decimal("0.00")
            )
        except Exception:
            precio = Decimal("0.00")

        # Resolver categoría o crearla si no existe
        cat_id = categorias_map.get(cat_cod)
        if not cat_id:
            nueva_cat = Categoria(
                company_id=company_id,
                codigo=cat_cod,
                nombre=cat_cod.capitalize(),
            )
            session.add(nueva_cat)
            await session.flush()
            cat_id = nueva_cat.id
            categorias_map[cat_cod] = cat_id

        # Resolver alícuota de IVA
        ali_id = alicuotas_map.get(ali_cod) or list(alicuotas_map.values())[0]

        # Verificar si producto ya existe
        stmt_exist = select(Product).where(
            Product.company_id == company_id, Product.codigo == codigo
        )
        res_exist = await session.execute(stmt_exist)
        existente = res_exist.scalar_one_or_none()

        if existente:
            existente.descripcion = descripcion
            existente.precio_base_usd = precio
            existente.categoria_id = cat_id
            existente.alicuota_iva_id = ali_id
            existente.version += 1
        else:
            prod = Product(
                company_id=company_id,
                codigo=codigo,
                descripcion=descripcion,
                categoria_id=cat_id,
                alicuota_iva_id=ali_id,
                precio_base_usd=precio,
            )
            session.add(prod)
            insertados += 1

    await session.flush()
    return {"total_filas": len(filas) - 1, "insertados": insertados, "errores": errores}
