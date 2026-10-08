"""Prueba de carga y concurrencia simulando 10 usuarios concurrentes (Fase 8)."""

import asyncio
import uuid

import httpx
import pytest

from app.control.aprovisionamiento import aprovisionar_tenant
from app.main import app


@pytest.fixture(scope="session")
async def carga_tenant_slug() -> str:
    slug = f"load-{uuid.uuid4().hex[:6]}"
    await aprovisionar_tenant(
        slug=slug,
        nombre="Galaxy Load Test C.A.",
        plan="enterprise",
        admin_email="admin@load.local",
        admin_password="Password123!",
    )
    return slug


@pytest.mark.asyncio
async def test_concurrencia_10_usuarios(carga_tenant_slug: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login inicial
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "cliente": carga_tenant_slug,
                "usuario": "admin",
                "password": "Password123!",
            },
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Cargar datos base
        alm_resp = await client.post(
            "/api/v1/admin/almacenes",
            headers=headers,
            json={"codigo": "LOAD-ALM", "nombre": "Almacén Pruebas Carga"},
        )
        assert alm_resp.status_code == 201

        # 3. Tarea concurrente de usuario
        async def simular_usuario(_usuario_id: int):
            for _i in range(3):
                # Consulta de salud
                resp_s = await client.get("/salud")
                assert resp_s.status_code == 200

                # Consulta de perfil
                resp_m = await client.get("/api/v1/auth/me", headers=headers)
                assert resp_m.status_code == 200

                # Consulta de catálogo de productos
                resp_p = await client.get("/api/v1/admin/productos", headers=headers)
                assert resp_p.status_code == 200

                # Consulta de almacenes
                resp_a = await client.get("/api/v1/admin/almacenes", headers=headers)
                assert resp_a.status_code == 200

        # Lanzar 10 usuarios concurrentes en paralelo
        tareas = [simular_usuario(u) for u in range(10)]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

        for res in resultados:
            assert not isinstance(res, Exception), f"Fallo en concurrencia: {res}"
