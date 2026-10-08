import uuid
from decimal import Decimal

import httpx
import pytest

from app.control.aprovisionamiento import aprovisionar_tenant
from app.main import app


@pytest.fixture(scope="session")
async def tenant_slug() -> str:
    slug = f"erp-{uuid.uuid4().hex[:6]}"
    await aprovisionar_tenant(
        slug=slug,
        nombre="Galaxy Enterprise Test",
        plan="enterprise",
        admin_email="admin@galaxy.local",
        admin_password="Password123!",
    )
    return slug


@pytest.mark.asyncio
async def test_ciclo_completo_fases_1_a_5(tenant_slug: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # ==============================================================================
        # 0. LOGIN Y OBTENCIÓN DE TOKEN
        # ==============================================================================
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "cliente": tenant_slug,
                "usuario": "admin",
                "password": "Password123!",
            },
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Perfil y datos iniciales
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["company_id"] is not None

        # ==============================================================================
        # FASE 1: ADMINISTRACIÓN Y CATÁLOGOS
        # ==============================================================================
        # 1.1 Registrar Tasa de Cambio Oficial (USD -> 36.500000 VES)
        tasa_resp = await client.post(
            "/api/v1/admin/tasas",
            headers=headers,
            json={
                "fecha": "2026-10-08",
                "moneda": "USD",
                "fuente": "BCV",
                "valor": "36.500000",
            },
        )
        assert tasa_resp.status_code == 201

        # 1.2 Crear Categoría de Productos
        cat_resp = await client.post(
            "/api/v1/admin/categorias",
            headers=headers,
            json={
                "codigo": "BEBIDAS",
                "nombre": "Bebidas y Refrescos",
                "descripcion": "Categoría general de bebidas",
            },
        )
        assert cat_resp.status_code == 201
        cat_id = cat_resp.json()["id"]

        # 1.3 Obtener Alícuota General (16%) y Almacén inicial
        from sqlalchemy import select

        from app.control.db import control_session
        from app.control.repository import obtener_tenant_por_slug
        from app.modules.admin.models import AlicuotaIva, Warehouse
        from app.tenancy.motores import get_gestor_motores

        async with control_session() as cs:
            t_obj = await obtener_tenant_por_slug(cs, tenant_slug)
            assert t_obj is not None
        gestor = get_gestor_motores()
        eng = await gestor.obtener(t_obj)

        async with eng.connect() as conn:
            w_res = await conn.execute(select(Warehouse.id).limit(1))
            warehouse_id = str(w_res.scalar_one())
            ali_stmt = select(AlicuotaIva.id).where(AlicuotaIva.codigo == "GENERAL")
            ali_res = await conn.execute(ali_stmt)
            alicuota_id = str(ali_res.scalar_one())

        # 1.4 Crear Producto Bimoneda
        prod_resp = await client.post(
            "/api/v1/admin/productos",
            headers=headers,
            json={
                "categoria_id": cat_id,
                "alicuota_iva_id": alicuota_id,
                "codigo": "AGUA-500ML",
                "codigo_barras": "7591234567890",
                "descripcion": "Agua Mineral 500ml",
                "unidad": "BOT",
                "costo_estandar": "0.5000",
                "precio_base_usd": "1.0000",
                "minimo": "10.0000",
                "maximo": "500.0000",
            },
        )
        assert prod_resp.status_code == 201
        prod_id = prod_resp.json()["id"]

        # 1.5 Crear Proveedor (con Retención Configurable: Sí retiene IVA 75%)
        prov_resp = await client.post(
            "/api/v1/admin/proveedores",
            headers=headers,
            json={
                "rif": "J-12345678-0",
                "razon_social": "Distribuidora de Aguas Polar C.A.",
                "contribuyente": "ESPECIAL",
                "retiene_iva": True,
                "porcentaje_retencion_iva": "75.00",
                "retiene_islr": True,
                "porcentaje_retencion_islr": "2.00",
            },
        )
        assert prov_resp.status_code == 201
        prov_id = prov_resp.json()["id"]

        # 1.6 Crear Cliente (con Retención Configurable: Sí nos retiene IVA 75%)
        cli_resp = await client.post(
            "/api/v1/admin/clientes",
            headers=headers,
            json={
                "tipo_identificacion": "J",
                "identificacion": "98765432-1",
                "nombre": "Automercados Plaza C.A.",
                "contribuyente": "ESPECIAL",
                "nos_retiene_iva": True,
                "porcentaje_retencion_iva": "75.00",
                "limite_credito": "1000.00",
            },
        )
        assert cli_resp.status_code == 201
        cli_id = cli_resp.json()["id"]

        # 1.7 Crear Instrumento de Pago
        inst_resp = await client.post(
            "/api/v1/admin/instrumentos-pago",
            headers=headers,
            json={
                "codigo": "TRANS-BS",
                "nombre": "Transferencia Bancaria VES",
                "tipo": "TRANSFERENCIA",
                "moneda": "VES",
            },
        )
        assert inst_resp.status_code == 201
        inst_id = inst_resp.json()["id"]

        # ==============================================================================
        # FASE 2: INVENTARIO, KARDEX Y SALDOS
        # ==============================================================================
        # 2.1 Carga inicial de stock manual (100 unidades)
        cargo_resp = await client.post(
            "/api/v1/inventario/movimientos-manuales",
            headers=headers,
            json={
                "warehouse_id": warehouse_id,
                "product_id": prod_id,
                "tipo": "CARGO",
                "cantidad": "100.0000",
                "costo_std": "0.5000",
                "motivo": "Carga inicial de inventario",
            },
        )
        assert cargo_resp.status_code == 201
        assert Decimal(cargo_resp.json()["cantidad"]) == Decimal("100.0000")

        # 2.2 Validar invariante de Kardex
        invar_resp = await client.get(
            f"/api/v1/inventario/verificar-invariante?warehouse_id={warehouse_id}&product_id={prod_id}",
            headers=headers,
        )
        assert invar_resp.status_code == 200
        assert invar_resp.json()["invariante_valida"] is True

        # ==============================================================================
        # FASE 3: COMPRAS Y VENTAS
        # ==============================================================================
        # 3.1 Registrar Compra a Proveedor Polar (50 unidades a $0.50 = $25 base + $4 IVA = $29)
        compra_resp = await client.post(
            "/api/v1/compras",
            headers=headers,
            json={
                "proveedor_id": prov_id,
                "warehouse_id": warehouse_id,
                "numero_factura": "POL-00129",
                "numero_control": "00-008912",
                "fecha_emision": "2026-10-08",
                "moneda": "USD",
                "items": [
                    {
                        "product_id": prod_id,
                        "cantidad": "50.0000",
                        "costo_unitario": "0.5000",
                        "alicuota_iva": "16.00",
                    }
                ],
            },
        )
        assert compra_resp.status_code == 201
        compra_data = compra_resp.json()
        assert Decimal(compra_data["total_usd"]) == Decimal("29.00")
        assert compra_data["aplica_retencion_iva"] is True
        # 75% de $4.00 = $3.00
        assert Decimal(compra_data["monto_retencion_iva"]) == Decimal("3.00")

        # Verificar que el stock subió a 150 unidades (100 inicial + 50 compra)
        saldos_post_compra = await client.get(
            f"/api/v1/inventario/saldos?warehouse_id={warehouse_id}", headers=headers
        )
        assert saldos_post_compra.status_code == 200
        p_saldo = [s for s in saldos_post_compra.json() if s["product_id"] == prod_id][0]
        assert Decimal(p_saldo["cantidad"]) == Decimal("150.0000")

        # 3.2 Emitir Factura de Venta a Automercados Plaza
        # 30 unidades a $1.00 = $30 base + $4.80 IVA = $34.80 total
        factura_resp = await client.post(
            "/api/v1/ventas/facturas",
            headers=headers,
            json={
                "cliente_id": cli_id,
                "warehouse_id": warehouse_id,
                "fecha_emision": "2026-10-08",
                "moneda": "USD",
                "items": [
                    {
                        "product_id": prod_id,
                        "cantidad": "30.0000",
                        "precio_unitario": "1.0000",
                        "alicuota_iva": "16.00",
                    }
                ],
            },
        )
        assert factura_resp.status_code == 201
        fac_data = factura_resp.json()
        assert Decimal(fac_data["total_usd"]) == Decimal("34.80")
        assert fac_data["numero_factura"] == "FAC-000001"
        assert fac_data["numero_control"] == "00-000001"
        # Cliente nos retiene IVA 75%: 75% de $4.80 = $3.60
        assert Decimal(fac_data["monto_retencion_iva"]) == Decimal("3.60")
        # Saldo pendiente = $34.80 - $3.60 = $31.20
        assert Decimal(fac_data["saldo_pendiente_usd"]) == Decimal("31.20")

        # Verificar que el stock bajó a 120 unidades (150 - 30 venta)
        saldos_post_venta = await client.get(
            f"/api/v1/inventario/saldos?warehouse_id={warehouse_id}", headers=headers
        )
        p_saldo_post = [s for s in saldos_post_venta.json() if s["product_id"] == prod_id][0]
        assert Decimal(p_saldo_post["cantidad"]) == Decimal("120.0000")

        # ==============================================================================
        # FASE 4: FINANZAS, BANCOS, CXC Y CXP
        # ==============================================================================
        # 4.1 Crear Cuenta Bancaria
        banco_resp = await client.post(
            "/api/v1/bancos/cuentas",
            headers=headers,
            json={
                "banco_nombre": "Banco Banesco",
                "numero_cuenta": "0134-1234-56-1234567890",
                "tipo": "CORRIENTE",
                "moneda": "VES",
                "saldo_inicial": "1000.00",
            },
        )
        assert banco_resp.status_code == 201
        banco_id = banco_resp.json()["id"]

        # 4.2 Consultar CxC generada automáticamente por la factura de venta
        cxc_list = await client.get("/api/v1/finanzas/cxc", headers=headers)
        assert cxc_list.status_code == 200
        cxc_item = cxc_list.json()[0]
        assert cxc_item["factura_id"] == fac_data["id"]
        assert Decimal(cxc_item["saldo_pendiente_usd"]) == Decimal("31.20")

        # 4.3 Aplicar Cobro del cliente ($31.20 a tasa 36.5 = 1138.80 Bs ingresados a banco)
        cobro_resp = await client.post(
            "/api/v1/finanzas/cobros",
            headers=headers,
            json={
                "cxc_id": cxc_item["id"],
                "fecha": "2026-10-08",
                "monto_cobrado_usd": "31.20",
                "monto_cobrado_ves": "1138.80",
                "instrumento_pago_id": inst_id,
                "cuenta_bancaria_id": banco_id,
                "referencia": "TRANSF-998877",
            },
        )
        assert cobro_resp.status_code == 201

        # Verificar que CxC quedó PAGADA
        cxc_post = await client.get("/api/v1/finanzas/cxc", headers=headers)
        assert cxc_post.json()[0]["estado"] == "PAGADA"

        # 4.4 Consultar CxP generada por la compra
        cxp_list = await client.get("/api/v1/finanzas/cxp", headers=headers)
        assert cxp_list.status_code == 200
        cxp_item = cxp_list.json()[0]
        assert cxp_item["compra_id"] == compra_data["id"]

        # 4.5 Pagar al proveedor polar
        pago_resp = await client.post(
            "/api/v1/finanzas/pagos",
            headers=headers,
            json={
                "cxp_id": cxp_item["id"],
                "fecha": "2026-10-08",
                "monto_pagado_usd": str(cxp_item["saldo_pendiente_usd"]),
                "monto_pagado_ves": "930.75",
                "instrumento_pago_id": inst_id,
                "referencia": "PAGO-POL-01",
            },
        )
        assert pago_resp.status_code == 201

        # Verificar que CxP quedó PAGADA
        cxp_post = await client.get("/api/v1/finanzas/cxp", headers=headers)
        assert cxp_post.json()[0]["estado"] == "PAGADA"

        # 4.6 Antigüedad de saldos
        antig_resp = await client.get("/api/v1/finanzas/antiguedad-cxc", headers=headers)
        assert antig_resp.status_code == 200
        assert Decimal(antig_resp.json()["total"]) == Decimal("0.00")  # Ya todo cobrado

        # ==============================================================================
        # FASE 5: IMPUESTOS, LIBROS SENIAT Y EXPORTACIÓN EXCEL
        # ==============================================================================
        # 5.1 Libro de Ventas mensual
        lv_resp = await client.get(
            "/api/v1/impuestos/libro-ventas?anio=2026&mes=10", headers=headers
        )
        assert lv_resp.status_code == 200
        lv_data = lv_resp.json()
        assert len(lv_data["filas"]) == 1
        assert lv_data["filas"][0]["numero_factura"] == "FAC-000001"
        assert Decimal(lv_data["total_ventas_ves"]) > Decimal("0.00")

        # 5.2 Descarga de Libro de Ventas en Excel (.xlsx)
        excel_v_resp = await client.get(
            "/api/v1/impuestos/libro-ventas/excel?anio=2026&mes=10", headers=headers
        )
        assert excel_v_resp.status_code == 200
        assert len(excel_v_resp.content) > 1000
        assert "spreadsheetml" in excel_v_resp.headers["content-type"]

        # 5.3 Libro de Compras mensual
        lc_resp = await client.get(
            "/api/v1/impuestos/libro-compras?anio=2026&mes=10", headers=headers
        )
        assert lc_resp.status_code == 200
        lc_data = lc_resp.json()
        assert len(lc_data["filas"]) == 1
        assert lc_data["filas"][0]["numero_factura"] == "POL-00129"
        assert Decimal(lc_data["total_compras_ves"]) > Decimal("0.00")

        # 5.4 Comprobante de Retención IVA emitido a Polar
        ret_resp = await client.get("/api/v1/impuestos/retenciones-iva", headers=headers)
        assert ret_resp.status_code == 200
        ret_items = ret_resp.json()
        assert len(ret_items) == 1
        assert ret_items[0]["proveedor_id"] == prov_id
        assert Decimal(ret_items[0]["monto_retenido_ves"]) > Decimal("0.00")
