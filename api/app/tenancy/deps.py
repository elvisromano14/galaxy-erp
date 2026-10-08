from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.control.db import control_session
from app.core.errores import GalaxyERPException
from app.core.seguridad import TokenData, decodificar_access_token
from app.tenancy.motores import get_gestor_motores
from app.tenancy.registro import exigir_tenant_activo, obtener_registro_tenant


async def get_token_auth(
    authorization: Annotated[str | None, Header()] = None,
) -> TokenData:
    """Extrae y valida el JWT de la cabecera Authorization."""
    if not authorization:
        raise GalaxyERPException(
            code="AUTENTICACION_REQUERIDA",
            title="Autenticación requerida",
            status=401,
            detail="Se requiere cabecera Authorization con formato 'Bearer <token>'.",
        )

    partes = authorization.split()
    if len(partes) != 2 or partes[0].lower() != "bearer":
        raise GalaxyERPException(
            code="TOKEN_INVALIDO",
            title="Token inválido",
            status=401,
            detail="Formato de token de autorización incorrecto.",
        )

    try:
        return decodificar_access_token(partes[1])
    except Exception as exc:
        raise GalaxyERPException(
            code="TOKEN_EXPIRADO_O_INVALIDO",
            title="Token no válido",
            status=401,
            detail=f"El token no es válido o ha expirado: {exc}",
        ) from exc


async def sesion_tenant(
    token_data: Annotated[TokenData, Depends(get_token_auth)],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de sesión de base de datos por tenant.
    Aísla la conexión en la base física del cliente y establece company_id con SET LOCAL.
    """
    async with control_session() as c_session:
        tenant = await obtener_registro_tenant(c_session, token_data.tid)

    exigir_tenant_activo(tenant)

    gestor = get_gestor_motores()
    motor = await gestor.obtener(tenant)

    async with AsyncSession(motor, expire_on_commit=False) as s, s.begin():
        # Establece la empresa activa para la transacción actual (Sección 9.3)
        await s.execute(
            text("SELECT set_config('app.company_id', :c, true)"),
            {"c": str(token_data.cid)},
        )
        yield s
