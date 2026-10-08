"""Servicio de obtención y sincronización de tasas de cambio del Banco Central de Venezuela."""

from datetime import date
from decimal import Decimal

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dinero import cuantizar_tasa
from app.core.tiempo import hoy_ccs
from app.modules.admin.models import TasaCambio
from app.modules.admin.schemas import TasaCambioCreate
from app.modules.admin.service import AdminService

logger = structlog.get_logger()

BCV_API_URL = "https://pydolarvenezuela-api.vercel.app/api/v1/dollar/page?page=bcv"


async def consultar_tasa_bcv_remota() -> Decimal | None:
    """Consulta la tasa oficial del BCV desde servicio público o scraping seguro."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(BCV_API_URL)
            if resp.status_code == 200:
                data = resp.json()
                # pydolar format: {"monitors": {"usd": {"price": 36.50}}}
                monitors = data.get("monitors", {})
                usd = monitors.get("usd", {})
                precio = usd.get("price")
                if precio is not None:
                    return cuantizar_tasa(Decimal(str(precio)))
    except Exception as exc:
        logger.warning("Fallo al consultar tasa BCV remota", error=str(exc))
    return None


async def sincronizar_tasa_bcv(
    session: AsyncSession, fecha: date | None = None
) -> TasaCambio | None:
    """Obtiene la tasa remota y la persiste en tasa_cambio con fuente BCV."""
    fecha_operacion = fecha or hoy_ccs()
    tasa_valor = await consultar_tasa_bcv_remota()
    if not tasa_valor:
        return None

    try:
        return await AdminService.registrar_tasa(
            session,
            TasaCambioCreate(
                fecha=fecha_operacion,
                moneda="USD",
                fuente="BCV",
                valor=tasa_valor,
            ),
        )
    except Exception as exc:
        logger.info("Tasa ya registrada para hoy o error al guardar", error=str(exc))
        return None
