import uuid

import httpx
import pytest

from app.control.aprovisionamiento import aprovisionar_tenant
from app.control.db import control_session
from app.control.repository import actualizar_estado_tenant
from app.main import app


@pytest.fixture(scope="session")
async def tenant_acme() -> str:
    slug = f"t1-{uuid.uuid4().hex[:6]}"
    await aprovisionar_tenant(
        slug=slug,
        nombre="Tenant 1 Test",
        plan="pro",
        admin_email="admin@t1.com",
        admin_password="Password123!",
    )
    return slug


@pytest.fixture(scope="session")
async def tenant_dist() -> str:
    slug = f"t2-{uuid.uuid4().hex[:6]}"
    await aprovisionar_tenant(
        slug=slug,
        nombre="Tenant 2 Test",
        plan="pro",
        admin_email="admin@t2.com",
        admin_password="Password123!",
    )
    return slug


@pytest.mark.asyncio
async def test_flujo_login_y_me(tenant_acme: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login exitoso
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "cliente": tenant_acme,
                "usuario": "admin",
                "password": "Password123!",
            },
        )
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        token = data["access_token"]
        refresh = data["refresh_token"]

        # 2. Consultar /me
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["username"] == "admin"
        assert me_data["email"] == "admin@t1.com"
        assert "administrador" in me_data["roles"]
        assert len(me_data["permisos"]) > 0

        # 3. Refresh token
        ref_resp = await client.post(
            "/api/v1/auth/refresh",
            json={
                "cliente": tenant_acme,
                "refresh_token": refresh,
            },
        )
        assert ref_resp.status_code == 200
        ref_data = ref_resp.json()
        assert ref_data["access_token"] != token
        assert ref_data["refresh_token"] != refresh


@pytest.mark.asyncio
async def test_tenant_suspendido_devuelve_403(tenant_acme: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Obtener token válido antes de suspender
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "cliente": tenant_acme,
                "usuario": "admin",
                "password": "Password123!",
            },
        )
        token = login_resp.json()["access_token"]
        tid = login_resp.json()["tenant_id"]

        # Suspender tenant en erp_control
        from app.tenancy.registro import invalidar_cache_tenant

        async with control_session() as c_session:
            await actualizar_estado_tenant(c_session, uuid.UUID(tid), "suspendido")
        invalidar_cache_tenant(uuid.UUID(tid))

        # Petición a /me debe fallar con 403 TENANT_SUSPENDIDO
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 403
        assert me_resp.json()["code"] == "TENANT_SUSPENDIDO"

        # Reactivar para no afectar otras pruebas
        async with control_session() as c_session:
            await actualizar_estado_tenant(c_session, uuid.UUID(tid), "activo")
        invalidar_cache_tenant(uuid.UUID(tid))


@pytest.mark.asyncio
async def test_aislamiento_entre_clientes(tenant_acme: str, tenant_dist: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Login en tenant 1
        resp_t1 = await client.post(
            "/api/v1/auth/login",
            json={"cliente": tenant_acme, "usuario": "admin", "password": "Password123!"},
        )
        data_t1 = resp_t1.json()

        # Login en tenant 2
        resp_t2 = await client.post(
            "/api/v1/auth/login",
            json={"cliente": tenant_dist, "usuario": "admin", "password": "Password123!"},
        )
        data_t2 = resp_t2.json()

        assert data_t1["tenant_id"] != data_t2["tenant_id"]
        assert data_t1["company_id"] != data_t2["company_id"]

        # Token de tenant 1 no puede refrescarse en tenant 2
        ref_cruzado = await client.post(
            "/api/v1/auth/refresh",
            json={"cliente": tenant_dist, "refresh_token": data_t1["refresh_token"]},
        )
        assert ref_cruzado.status_code == 401
