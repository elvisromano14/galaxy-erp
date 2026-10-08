import httpx
import pytest

from app.control.seed_test import garantizar_tenant_test
from app.main import app


@pytest.mark.asyncio
async def test_tenant_test_permanente_y_canario() -> None:
    # 1. Asegurar aprovisionamiento y sembrado del tenant canario 'test'
    tenant = await garantizar_tenant_test()
    assert tenant.slug == "test"
    assert tenant.db_name == "erp_c_test"
    assert tenant.es_canario is True
    assert tenant.estado == "activo"

    # 2. Conexión HTTP contra la API
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Login oficial
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "cliente": "test",
                "usuario": "admin",
                "password": "GalaxyTest2026!",
            },
        )
        assert login_resp.status_code == 200, f"Error en login: {login_resp.text}"
        data = login_resp.json()
        assert "access_token" in data
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Perfil autenticado
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        me = me_resp.json()
        assert me["username"] == "admin"
        assert me["email"] == "admin@galaxy.test"

        # Listar almacenes sembrados
        alm_resp = await client.get("/api/v1/admin/almacenes", headers=headers)
        assert alm_resp.status_code == 200
        almacenes = alm_resp.json()
        codigos_almacen = [a["codigo"] for a in almacenes]
        assert "PRINCIPAL" in codigos_almacen
        assert "TIENDA" in codigos_almacen

        # Listar productos sembrados
        prod_resp = await client.get("/api/v1/admin/productos", headers=headers)
        assert prod_resp.status_code == 200
        prods = prod_resp.json()
        codigos_prod = [p["codigo"] for p in prods]
        assert "HAR-PAN" in codigos_prod
        assert "ARR-PRI" in codigos_prod

        # Listar inventario (saldos)
        saldos_resp = await client.get("/api/v1/inventario/saldos", headers=headers)
        assert saldos_resp.status_code == 200
        saldos = saldos_resp.json()
        assert len(saldos) > 0

        # Listar clientes sembrados
        cli_resp = await client.get("/api/v1/admin/clientes", headers=headers)
        assert cli_resp.status_code == 200
        clientes = cli_resp.json()
        assert len(clientes) >= 2
        # Verificar que el cliente contribuyente especial tenga retención configurada
        cli_especial = next((c for c in clientes if c["identificacion"] == "20202020-1"), None)
        assert cli_especial is not None
        assert cli_especial["nos_retiene_iva"] is True
        assert float(cli_especial["porcentaje_retencion_iva"]) == 75.0

        # Listar proveedores sembrados
        prov_resp = await client.get("/api/v1/admin/proveedores", headers=headers)
        assert prov_resp.status_code == 200
        proveedores = prov_resp.json()
        assert len(proveedores) >= 2
        prov_especial = next((p for p in proveedores if p["rif"] == "J-40404040-3"), None)
        assert prov_especial is not None
        assert prov_especial["retiene_iva"] is True
        assert float(prov_especial["porcentaje_retencion_iva"]) == 75.0
