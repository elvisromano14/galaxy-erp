import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.control.db import control_session
from app.control.repository import (
    actualizar_estado_tenant,
    crear_tenant,
    finalizar_job,
    obtener_tenant_por_id,
    obtener_tenant_por_slug,
    registrar_job,
)


@pytest.fixture
async def session() -> AsyncSession:
    async with control_session() as s:
        yield s


@pytest.mark.asyncio
async def test_crear_y_obtener_tenant(session: AsyncSession) -> None:
    slug = f"acme-{uuid.uuid4().hex[:6]}"
    tenant = await crear_tenant(
        session,
        slug=slug,
        nombre="Acme Corp Test",
        plan="pro",
        db_name=f"erp_c_{slug}",
        modulos=["ventas", "inventario"],
    )

    assert tenant.id is not None
    assert tenant.slug == slug
    assert tenant.estado == "aprovisionando"
    assert len(tenant.modulos) == 2

    # Obtener por slug
    por_slug = await obtener_tenant_por_slug(session, slug)
    assert por_slug is not None
    assert por_slug.id == tenant.id

    # Obtener por id
    por_id = await obtener_tenant_por_id(session, tenant.id)
    assert por_id is not None
    assert por_id.slug == slug


@pytest.mark.asyncio
async def test_actualizar_estado_tenant(session: AsyncSession) -> None:
    slug = f"dist-{uuid.uuid4().hex[:6]}"
    tenant = await crear_tenant(
        session,
        slug=slug,
        nombre="Distribuidora Test",
        plan="basico",
        db_name=f"erp_c_{slug}",
    )

    actualizado = await actualizar_estado_tenant(session, tenant.id, "activo")
    assert actualizado is not None
    assert actualizado.estado == "activo"


@pytest.mark.asyncio
async def test_slug_invalido_falla_constraint(session: AsyncSession) -> None:
    # Slug con mayúsculas debe fallar por el check constraint
    with pytest.raises(IntegrityError):
        await crear_tenant(
            session,
            slug="SLUG_INVALIDO",
            nombre="Nombre Invalido",
            plan="pro",
            db_name="erp_c_invalido",
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_ciclo_job(session: AsyncSession) -> None:
    job = await registrar_job(
        session,
        tenant_id=None,
        tipo="CREAR",
        detalle={"param": "valor"},
    )
    assert job.estado == "EN_CURSO"
    assert job.terminado_en is None

    finalizado = await finalizar_job(
        session,
        job.id,
        estado="OK",
        detalle={"resultado": "exitoso"},
    )
    assert finalizado is not None
    assert finalizado.estado == "OK"
    assert finalizado.terminado_en is not None
