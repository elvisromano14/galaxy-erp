import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.control.models import Tenant
from app.control.repository import obtener_tenant_por_id, obtener_tenant_por_slug
from app.core.errores import GalaxyERPException

# Caché en memoria local para rápida resolución
_cache_registro: dict[str, Tenant] = {}


async def obtener_registro_tenant(
    session_control: AsyncSession,
    tenant_id: uuid.UUID,
) -> Tenant:
    """Resuelve la metadata de conexión del tenant con caché."""
    clave = str(tenant_id)
    if clave in _cache_registro:
        return _cache_registro[clave]

    tenant = await obtener_tenant_por_id(session_control, tenant_id)
    if not tenant:
        raise GalaxyERPException(
            code="TENANT_NO_ENCONTRADO",
            title="Cliente no encontrado",
            status=404,
            detail=f"No se encontró el tenant con id '{tenant_id}'.",
        )

    _cache_registro[clave] = tenant
    return tenant


async def obtener_registro_por_slug(
    session_control: AsyncSession,
    slug: str,
) -> Tenant:
    """Busca el tenant por su código o slug comercial."""
    for t in _cache_registro.values():
        if t.slug == slug:
            return t

    tenant = await obtener_tenant_por_slug(session_control, slug)
    if not tenant:
        raise GalaxyERPException(
            code="TENANT_NO_ENCONTRADO",
            title="Cliente no encontrado",
            status=404,
            detail=f"No se encontró el cliente '{slug}'.",
        )

    _cache_registro[str(tenant.id)] = tenant
    return tenant


def invalidar_cache_tenant(tenant_id: uuid.UUID) -> None:
    """Limpia la caché de registro al actualizar estado o configuración."""
    clave = str(tenant_id)
    _cache_registro.pop(clave, None)


def exigir_tenant_activo(tenant: Tenant) -> None:
    """Verifica que el tenant esté en estado activo según Sección 10.3."""
    if tenant.estado == "activo":
        return

    if tenant.estado == "suspendido":
        raise GalaxyERPException(
            code="TENANT_SUSPENDIDO",
            title="Servicio suspendido",
            status=403,
            detail="La cuenta se encuentra temporalmente suspendida.",
        )
    elif tenant.estado == "aprovisionando":
        raise GalaxyERPException(
            code="TENANT_EN_PREPARACION",
            title="Servicio en preparación",
            status=503,
            detail="La cuenta se está aprovisionando. Intente en unos momentos.",
        )
    elif tenant.estado == "archivado":
        raise GalaxyERPException(
            code="TENANT_ARCHIVADO",
            title="Cuenta archivada",
            status=410,
            detail="La cuenta ha sido archivada y no admite operaciones.",
        )
    else:
        raise GalaxyERPException(
            code="TENANT_NO_DISPONIBLE",
            title="Servicio no disponible",
            status=503,
            detail=f"El tenant se encuentra en estado '{tenant.estado}'.",
        )
