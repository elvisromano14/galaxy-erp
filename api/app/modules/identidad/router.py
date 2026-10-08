import hashlib
import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control.db import control_session
from app.core.config import settings
from app.core.errores import GalaxyERPException
from app.core.middleware import verificar_rate_limit_login
from app.core.seguridad import (
    TokenData,
    crear_access_token,
    verificar_password,
)
from app.core.tiempo import ahora
from app.modules.admin.models import Company
from app.modules.identidad.models import SesionRefresh, Usuario
from app.modules.identidad.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    UserMeResponse,
)
from app.tenancy.deps import get_token_auth, sesion_tenant
from app.tenancy.motores import get_gestor_motores
from app.tenancy.registro import exigir_tenant_activo, obtener_registro_por_slug

router = APIRouter(prefix="/auth", tags=["Identidad y Sesión"])


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(verificar_rate_limit_login)],
)
async def login(req: LoginRequest) -> LoginResponse:
    # 1. Obtener tenant de erp_control
    async with control_session() as c_session:
        tenant = await obtener_registro_por_slug(c_session, req.cliente)

    exigir_tenant_activo(tenant)

    # 2. Conectar a la base física del cliente
    gestor = get_gestor_motores()
    motor = await gestor.obtener(tenant)

    async with AsyncSession(motor, expire_on_commit=False) as session:
        # Buscar usuario
        query = select(Usuario).where(
            (Usuario.username == req.usuario) | (Usuario.email == req.usuario)
        )
        res = await session.execute(query)
        usuario = res.scalar_one_or_none()

        if not usuario or not usuario.activo:
            raise GalaxyERPException(
                code="CREDENCIALES_INVALIDAS",
                title="Credenciales incorrectas",
                status=401,
                detail="Usuario o contraseña incorrectos.",
            )

        if usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora():
            raise GalaxyERPException(
                code="USUARIO_BLOQUEADO",
                title="Usuario bloqueado",
                status=403,
                detail="Cuenta bloqueada temporalmente por intentos fallidos.",
            )

        if not verificar_password(usuario.password_hash, req.password):
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= 5:
                usuario.bloqueado_hasta = ahora() + timedelta(minutes=30)
            await session.commit()
            raise GalaxyERPException(
                code="CREDENCIALES_INVALIDAS",
                title="Credenciales incorrectas",
                status=401,
                detail="Usuario o contraseña incorrectos.",
            )

        # Login exitoso: restablecer intentos fallidos
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None

        roles_codigos = [r.codigo for r in usuario.roles]

        # Generar access token
        access_token = crear_access_token(
            tenant_id=tenant.id,
            company_id=usuario.company_id,
            usuario_id=usuario.id,
            roles=roles_codigos,
        )

        # Generar refresh token
        raw_refresh = secrets.token_urlsafe(64)
        hash_refresh = _hash_refresh_token(raw_refresh)
        expira_refresh = ahora() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        sesion_ref = SesionRefresh(
            usuario_id=usuario.id,
            token_hash=hash_refresh,
            expira_en=expira_refresh,
        )
        session.add(sesion_ref)
        await session.commit()

        expira_access = ahora() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        return LoginResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            tenant_id=tenant.id,
            company_id=usuario.company_id,
            usuario_id=usuario.id,
            roles=roles_codigos,
            expira_en=expira_access,
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(req: RefreshRequest) -> LoginResponse:
    async with control_session() as c_session:
        tenant = await obtener_registro_por_slug(c_session, req.cliente)

    exigir_tenant_activo(tenant)

    hash_refresh = _hash_refresh_token(req.refresh_token)

    gestor = get_gestor_motores()
    motor = await gestor.obtener(tenant)

    async with AsyncSession(motor, expire_on_commit=False) as session:
        query = select(SesionRefresh).where(
            SesionRefresh.token_hash == hash_refresh,
            SesionRefresh.revocado.is_(False),
            SesionRefresh.expira_en > ahora(),
        )
        res = await session.execute(query)
        sesion_ref = res.scalar_one_or_none()

        if not sesion_ref:
            raise GalaxyERPException(
                code="REFRESH_TOKEN_INVALIDO",
                title="Token de renovación inválido",
                status=401,
                detail="El token de renovación es inválido o ha expirado.",
            )

        # Rotar refresh token (revocar actual)
        sesion_ref.revocado = True

        # Obtener usuario
        q_user = select(Usuario).where(Usuario.id == sesion_ref.usuario_id)
        user_res = await session.execute(q_user)
        usuario = user_res.scalar_one()

        roles_codigos = [r.codigo for r in usuario.roles]

        access_token = crear_access_token(
            tenant_id=tenant.id,
            company_id=usuario.company_id,
            usuario_id=usuario.id,
            roles=roles_codigos,
        )

        nuevo_raw_refresh = secrets.token_urlsafe(64)
        nueva_sesion = SesionRefresh(
            usuario_id=usuario.id,
            token_hash=_hash_refresh_token(nuevo_raw_refresh),
            expira_en=ahora() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        session.add(nueva_sesion)
        await session.commit()

        expira_access = ahora() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        return LoginResponse(
            access_token=access_token,
            refresh_token=nuevo_raw_refresh,
            tenant_id=tenant.id,
            company_id=usuario.company_id,
            usuario_id=usuario.id,
            roles=roles_codigos,
            expira_en=expira_access,
        )


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    token: Annotated[TokenData, Depends(get_token_auth)],
    db: Annotated[AsyncSession, Depends(sesion_tenant)],
) -> UserMeResponse:
    # Obtener usuario en la empresa activa
    q_user = select(Usuario).where(Usuario.id == token.uid)
    res_user = await db.execute(q_user)
    usuario = res_user.scalar_one_or_none()

    if not usuario:
        raise GalaxyERPException(
            code="USUARIO_NO_ENCONTRADO",
            title="Usuario no encontrado",
            status=404,
            detail="El usuario no existe en la empresa activa.",
        )

    q_comp = select(Company).where(Company.id == token.cid)
    res_comp = await db.execute(q_comp)
    empresa = res_comp.scalar_one()

    permisos_set = set()
    for rol in usuario.roles:
        for perm in rol.permisos:
            permisos_set.add(perm.codigo)

    return UserMeResponse(
        id=usuario.id,
        username=usuario.username,
        email=usuario.email,  # type: ignore[arg-type]
        nombre_completo=usuario.nombre_completo,
        company_id=empresa.id,
        empresa_razon_social=empresa.razon_social,
        empresa_rif=empresa.rif,
        roles=[r.codigo for r in usuario.roles],
        permisos=sorted(permisos_set),
    )
