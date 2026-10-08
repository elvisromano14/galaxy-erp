#!/usr/bin/env python3
"""Script interactivo de verificación de conexión contra el tenant canario permanente 'test'."""

import asyncio
import sys
from decimal import Decimal

import httpx

from app.control.seed_test import (
    TEST_ADMIN_PASS,
    TEST_ADMIN_USER,
    TEST_SLUG,
    garantizar_tenant_test,
)
from app.main import app


async def main() -> None:
    print("=" * 70)
    print(" GALAXY ERP — VERIFICACIÓN Y PRUEBAS DEL TENANT CANARIO 'test'")
    print("=" * 70)

    # 1. Garantizar empresa 'test'
    print("\n[1/6] Verificando empresa de pruebas permanente en el plano de control...")
    tenant = await garantizar_tenant_test()
    print(f"  ✓ Slug: {tenant.slug}")
    print(f"  ✓ Base de datos: {tenant.db_name}")
    print(f"  ✓ Rol: Canario Oficial (es_canario={tenant.es_canario})")
    print(f"  ✓ Estado: {tenant.estado}")

    # 2. Conexión y autenticación HTTP
    print("\n[2/6] Autenticando usuario administrador...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "cliente": TEST_SLUG,
                "usuario": TEST_ADMIN_USER,
                "password": TEST_ADMIN_PASS,
            },
        )
        if login_resp.status_code != 200:
            print(f"  ✗ Error en autenticación: {login_resp.status_code} - {login_resp.text}")
            sys.exit(1)

        token = login_resp.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Slug": TEST_SLUG,
        }
        print("  ✓ Token JWT obtenido exitosamente.")

        # 3. Datos de perfil
        print("\n[3/6] Consultando datos de la sesión (/api/v1/auth/me)...")
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        me = me_resp.json()
        print(f"  ✓ Usuario activo: {me.get('username')} ({me.get('email')})")
        print(f"  ✓ ID Empresa: {me.get('company_id')}")

        # 4. Catálogos: Productos y Almacenes
        print("\n[4/6] Consultando catálogos de inventario...")
        prods_resp = await client.get("/api/v1/admin/productos", headers=headers)
        prods = prods_resp.json()
        print(f"  ✓ Total de productos registrados: {len(prods)}")
        for p in prods[:4]:
            print(f"    • [{p['codigo']}] {p['descripcion']} | Precio: ${p['precio_base_usd']}")

        alms_resp = await client.get("/api/v1/admin/almacenes", headers=headers)
        alms = alms_resp.json()
        print(f"  ✓ Total de almacenes: {len(alms)}")
        for a in alms:
            print(f"    • [{a['codigo']}] {a['nombre']}")

        # 5. Clientes y reglas de retención
        print("\n[5/6] Consultando clientes y configuración de retenciones...")
        clis_resp = await client.get("/api/v1/admin/clientes", headers=headers)
        clis = clis_resp.json()
        for c in clis:
            ret_str = f"Sí ({c['porcentaje_retencion_iva']}%)" if c["nos_retiene_iva"] else "No (0%)"
            print(f"    • {c['nombre']} ({c['identificacion']}) — Retiene IVA: {ret_str}")

        # 6. Instrumentos y Bancos
        print("\n[6/6] Consultando bancos e instrumentos de pago...")
        bancos_resp = await client.get("/api/v1/bancos/cuentas", headers=headers)
        if bancos_resp.status_code == 200:
            bancos = bancos_resp.json()
            print(f"  ✓ Cuentas bancarias configuradas: {len(bancos)}")
            for b in bancos:
                print(f"    • {b['banco_nombre']} ({b['moneda']}): Saldo actual {b['saldo_actual']}")

    print("\n" + "=" * 70)
    print(" ¡PRUEBA DE CONEXIÓN AL TENANT 'test' EXITOSA!")
    print("=" * 70)
    print("\nPara interactuar mediante la interfaz Swagger UI:")
    print("  1. Inicia el servidor con: make api  (o: uvicorn app.main:app --reload)")
    print("  2. Abre en tu navegador: http://localhost:8000/docs")
    print("  3. Usa el botón 'Authorize' con:")
    print(f"     • Cliente (Tenant): {TEST_SLUG}")
    print(f"     • Usuario: {TEST_ADMIN_USER}")
    print(f"     • Contraseña: {TEST_ADMIN_PASS}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
