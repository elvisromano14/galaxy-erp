import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.control.models import Tenant, TenantJob, TenantModulo
from app.core.tiempo import ahora


async def obtener_tenant_por_slug(session: AsyncSession, slug: str) -> Tenant | None:
    query = select(Tenant).where(Tenant.slug == slug)
    resultado = await session.execute(query)
    return resultado.scalar_one_or_none()


async def obtener_tenant_por_id(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    query = select(Tenant).where(Tenant.id == tenant_id)
    resultado = await session.execute(query)
    return resultado.scalar_one_or_none()


async def listar_tenants(session: AsyncSession) -> Sequence[Tenant]:
    query = select(Tenant).order_by(Tenant.creado_en.desc())
    resultado = await session.execute(query)
    return resultado.scalars().all()


async def crear_tenant(
    session: AsyncSession,
    *,
    slug: str,
    nombre: str,
    plan: str,
    db_name: str,
    db_host: str = "127.0.0.1",
    db_port: int = 6432,
    es_canario: bool = False,
    modulos: list[str] | None = None,
) -> Tenant:
    tenant = Tenant(
        slug=slug,
        nombre=nombre,
        plan=plan,
        db_name=db_name,
        db_host=db_host,
        db_port=db_port,
        es_canario=es_canario,
        estado="aprovisionando",
    )
    session.add(tenant)
    await session.flush()

    if modulos:
        for mod in modulos:
            modulo_obj = TenantModulo(tenant_id=tenant.id, modulo=mod, habilitado=True)
            session.add(modulo_obj)

    await session.commit()
    await session.refresh(tenant)
    return tenant


async def actualizar_estado_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    nuevo_estado: str,
) -> Tenant | None:
    query = (
        update(Tenant).where(Tenant.id == tenant_id).values(estado=nuevo_estado).returning(Tenant)
    )
    resultado = await session.execute(query)
    await session.commit()
    return resultado.scalar_one_or_none()


async def registrar_job(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    tipo: str,
    estado: str = "EN_CURSO",
    detalle: dict[str, Any] | None = None,
) -> TenantJob:
    job = TenantJob(
        tenant_id=tenant_id,
        tipo=tipo,
        estado=estado,
        detalle=detalle or {},
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def finalizar_job(
    session: AsyncSession,
    job_id: uuid.UUID,
    *,
    estado: str,
    detalle: dict[str, Any] | None = None,
) -> TenantJob | None:
    valores: dict[str, Any] = {
        "estado": estado,
        "terminado_en": ahora(),
    }
    if detalle is not None:
        valores["detalle"] = detalle

    query = update(TenantJob).where(TenantJob.id == job_id).values(**valores).returning(TenantJob)
    resultado = await session.execute(query)
    await session.commit()
    return resultado.scalar_one_or_none()
