"""Pruebas de integración para generación de PDFs (WeasyPrint)
y sincronización offline (Fase 6)."""

import uuid
from datetime import UTC, datetime

import httpx
import pytest

from app.control.aprovisionamiento import aprovisionar_tenant
from app.main import app


@pytest.fixture(scope="session")
async def sync_tenant_slug() -> str:
    slug = f"erp-{uuid.uuid4().hex[:6]}"
    await aprovisionar_tenant(
        slug=slug,
        nombre="Galaxy Sync Test C.A.",
        plan="enterprise",
        admin_email="admin@sync.local",
        admin_password="Password123!",
    )
    return slug


@pytest.mark.asyncio
async def test_generacion_pdf_y_sincronizacion_offline(sync_tenant_slug: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "cliente": sync_tenant_slug,
                "usuario": "admin",
                "password": "Password123!",
            },
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Perfil
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        user_id = me_resp.json()["id"]

        # 3. Tasa de cambio
        await client.post(
            "/api/v1/admin/tasas",
            headers=headers,
            json={
                "fecha": "2026-10-08",
                "moneda": "USD",
                "fuente": "BCV",
                "valor": "36.500000",
            },
        )

        # 4. Almacén
        alm_resp = await client.post(
            "/api/v1/admin/almacenes",
            headers=headers,
            json={"codigo": "MOVIL-1", "nombre": "Furgón Móvil Ruta 1"},
        )
        assert alm_resp.status_code == 201
        warehouse_id = alm_resp.json()["id"]

        # 5. Categoría y Producto
        cat_resp = await client.post(
            "/api/v1/admin/categorias",
            headers=headers,
            json={"codigo": "V-SNK", "nombre": "Snacks"},
        )
        assert cat_resp.status_code == 201
        cat_id = cat_resp.json()["id"]

        # Alicuotas
        from sqlalchemy import select

        from app.control.db import control_session
        from app.control.repository import obtener_tenant_por_slug
        from app.modules.admin.models import AlicuotaIva
        from app.tenancy.motores import get_gestor_motores

        async with control_session() as cs:
            t_obj = await obtener_tenant_por_slug(cs, sync_tenant_slug)
            assert t_obj is not None
        gestor = get_gestor_motores()
        eng = await gestor.obtener(t_obj)

        async with eng.connect() as conn:
            ali_stmt = select(AlicuotaIva.id).where(AlicuotaIva.codigo == "GENERAL")
            ali_res = await conn.execute(ali_stmt)
            alicuota_id = str(ali_res.scalar_one())

        prod_resp = await client.post(
            "/api/v1/admin/productos",
            headers=headers,
            json={
                "categoria_id": cat_id,
                "alicuota_iva_id": alicuota_id,
                "codigo": "GAL-001",
                "descripcion": "Galletas de Chocolate 100g",
                "unidad": "UND",
                "costo_estandar": "0.6000",
                "precio_base_usd": "1.5000",
            },
        )
        assert prod_resp.status_code == 201
        prod_id = prod_resp.json()["id"]

        # 6. Cliente
        cli_resp = await client.post(
            "/api/v1/admin/clientes",
            headers=headers,
            json={
                "tipo_identificacion": "J",
                "identificacion": "99887766-5",
                "nombre": "Bodega La Bendición",
                "direccion": "Calle Principal #12",
                "telefono": "0412-9988776",
                "email": "bodega@test.local",
                "nos_retiene_iva": True,
                "porcentaje_retencion_iva": "75.00",
            },
        )
        assert cli_resp.status_code == 201
        cliente_id = cli_resp.json()["id"]

        # 7. Registrar Dispositivo Sync
        disp_resp = await client.post(
            "/api/v1/sync/dispositivos",
            headers=headers,
            json={
                "nombre": "Terminal Vendedor #1",
                "identificador_unico": "DEV-TEST-0001",
                "usuario_id": user_id,
            },
        )
        assert disp_resp.status_code == 201
        disp_id = disp_resp.json()["id"]

        # 8. Solicitar Bloque de Correlativos para ventas fuera de línea
        bloque_resp = await client.post(
            "/api/v1/sync/bloques",
            headers=headers,
            json={
                "dispositivo_id": disp_id,
                "tipo_documento": "PRESUPUESTO",
                "serie": "OFF",
                "cantidad": 50,
            },
        )
        assert bloque_resp.status_code == 201
        b_data = bloque_resp.json()
        assert b_data["desde_numero"] == 1
        assert b_data["hasta_numero"] == 50

        # 9. Descargar Catálogos
        cat_sync_resp = await client.get("/api/v1/sync/catalogos?desde=0", headers=headers)
        assert cat_sync_resp.status_code == 200
        cat_data = cat_sync_resp.json()
        assert len(cat_data["productos"]) >= 1
        assert len(cat_data["clientes"]) >= 1
        assert cat_data["sync_token"] > 0

        # 10. Subir Lote de Operaciones (Pedido tomado en calle)
        op_id = str(uuid.uuid4())
        ops_resp = await client.post(
            "/api/v1/sync/operaciones",
            headers=headers,
            json={
                "dispositivo_id": disp_id,
                "operaciones": [
                    {
                        "client_op_id": op_id,
                        "tipo": "PEDIDO_VENTA",
                        "creado_en": datetime.now(UTC).isoformat(),
                        "tasa_usada": "36.500000",
                        "payload": {
                            "cliente_id": cliente_id,
                            "warehouse_id": warehouse_id,
                            "numero": "OFF-000001",
                            "moneda": "USD",
                            "items": [
                                {
                                    "product_id": prod_id,
                                    "cantidad": "5.0000",
                                    "precio_unitario": "1.5000",
                                }
                            ],
                        },
                    }
                ],
            },
        )
        assert ops_resp.status_code == 200
        batch_res = ops_resp.json()["resultados"]
        assert len(batch_res) == 1
        assert batch_res[0]["estado"] == "APLICADA"
        assert batch_res[0]["numero"] == "OFF-000001"

        # 11. Idempotencia: reenviar el mismo lote
        ops_dup_resp = await client.post(
            "/api/v1/sync/operaciones",
            headers=headers,
            json={
                "dispositivo_id": disp_id,
                "operaciones": [
                    {
                        "client_op_id": op_id,
                        "tipo": "PEDIDO_VENTA",
                        "creado_en": datetime.now(UTC).isoformat(),
                        "payload": {},
                    }
                ],
            },
        )
        assert ops_dup_resp.status_code == 200
        batch_dup = ops_dup_resp.json()["resultados"]
        assert batch_dup[0]["estado"] == "DUPLICADA"
        assert batch_dup[0]["numero"] == "OFF-000001"

        # 12. Cargar stock en almacén para poder facturar
        cargo_resp = await client.post(
            "/api/v1/inventario/movimientos-manuales",
            headers=headers,
            json={
                "warehouse_id": warehouse_id,
                "product_id": prod_id,
                "tipo": "CARGO",
                "cantidad": "20.0000",
                "costo_std": "0.6000",
                "motivo": "Carga de stock para prueba de factura y PDF",
            },
        )
        assert cargo_resp.status_code == 201

        # 13. Generar Factura y descargar en PDF
        fac_resp = await client.post(
            "/api/v1/ventas/facturas",
            headers=headers,
            json={
                "cliente_id": cliente_id,
                "warehouse_id": warehouse_id,
                "fecha_emision": "2026-10-08",
                "moneda": "USD",
                "tasa_cambio": "36.500000",
                "items": [
                    {
                        "product_id": prod_id,
                        "cantidad": "1.0000",
                        "precio_unitario": "2.0000",
                        "alicuota_iva": "16.00",
                    }
                ],
            },
        )
        assert fac_resp.status_code == 201
        fac_id = fac_resp.json()["id"]

        pdf_resp = await client.get(f"/api/v1/ventas/facturas/{fac_id}/pdf", headers=headers)
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert pdf_resp.content.startswith(b"%PDF")
        assert len(pdf_resp.content) > 1000
