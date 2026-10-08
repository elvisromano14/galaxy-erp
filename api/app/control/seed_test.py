"""Inicialización y garantía de la empresa persistente de pruebas ('test')."""

from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine

from app.control.aprovisionamiento import aprovisionar_tenant
from app.control.db import control_session
from app.control.models import Tenant
from app.control.repository import obtener_tenant_por_slug
from app.core.config import settings
from app.core.tiempo import hoy
from app.modules.admin.models import (
    AlicuotaIva,
    Categoria,
    Cliente,
    Company,
    InstrumentoPago,
    Product,
    Proveedor,
    TasaCambio,
    Vendedor,
    Warehouse,
    Zona,
)
from app.modules.bancos.models import CuentaBancaria
from app.modules.identidad.models import Usuario
from app.modules.inventario.models import StockBalance, StockMovement

TEST_SLUG = "test"
TEST_DB_NAME = "erp_c_test"
TEST_ADMIN_USER = "admin"
TEST_ADMIN_PASS = "GalaxyTest2026!"
TEST_ADMIN_EMAIL = "admin@galaxy.test"
TEST_RIF = "J-12345678-0"
TEST_RAZON_SOCIAL = "Empresa de Pruebas Galaxy C.A."


async def garantizar_tenant_test() -> Tenant:
    """Aprovisiona y garantiza la existencia de la base de datos 'test' con datos de prueba."""
    async with control_session() as cs:
        tenant = await obtener_tenant_por_slug(cs, TEST_SLUG)

    if not tenant:
        tenant = await aprovisionar_tenant(
            slug=TEST_SLUG,
            nombre=TEST_RAZON_SOCIAL,
            plan="enterprise",
            admin_email=TEST_ADMIN_EMAIL,
            admin_password=TEST_ADMIN_PASS,
            admin_nombre="Administrador de Pruebas",
            empresa_rif=TEST_RIF,
            empresa_razon_social=TEST_RAZON_SOCIAL,
            es_canario=True,
        )
    else:
        # Asegurar que esté activo y marcado como canario
        async with control_session() as cs:
            await cs.execute(
                update(Tenant)
                .where(Tenant.id == tenant.id)
                .values(estado="activo", es_canario=True)
            )
            await cs.commit()

    # Sembrar catálogos de prueba dentro de erp_c_test
    partes = settings.CONTROL_DB_OWNER_URL.rsplit("/", 1)
    url_test_owner = f"{partes[0]}/{TEST_DB_NAME}"
    engine = create_async_engine(url_test_owner)

    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine, expire_on_commit=False) as session:
        # 1. Obtener Company y Usuario Admin
        res_comp = await session.execute(select(Company).limit(1))
        company = res_comp.scalar_one()

        res_user = await session.execute(
            select(Usuario).where(Usuario.username == TEST_ADMIN_USER)
        )
        user = res_user.scalar_one()

        # 2. Registrar Tasa de Cambio del día (36.500000)
        fecha_ref = hoy()
        res_tasa = await session.execute(
            select(TasaCambio).where(
                TasaCambio.fecha == fecha_ref,
                TasaCambio.moneda == "USD",
                TasaCambio.fuente == "BCV",
            )
        )
        if not res_tasa.scalar_one_or_none():
            session.add(
                TasaCambio(
                    fecha=fecha_ref,
                    moneda="USD",
                    valor=Decimal("36.500000"),
                    fuente="BCV",
                )
            )

        # 3. Almacenes: PRINCIPAL y SUCURSAL
        res_alm_sec = await session.execute(
            select(Warehouse).where(
                Warehouse.company_id == company.id, Warehouse.codigo == "TIENDA"
            )
        )
        alm_sec = res_alm_sec.scalar_one_or_none()
        if not alm_sec:
            alm_sec = Warehouse(
                company_id=company.id,
                codigo="TIENDA",
                nombre="Punto de Venta / Tienda Central",
                activo=True,
            )
            session.add(alm_sec)

        res_alm_pri = await session.execute(
            select(Warehouse).where(
                Warehouse.company_id == company.id, Warehouse.codigo == "PRINCIPAL"
            )
        )
        alm_pri = res_alm_pri.scalar_one()

        await session.flush()

        # 4. Zonas y Vendedores
        res_zona = await session.execute(
            select(Zona).where(Zona.company_id == company.id, Zona.codigo == "CENTRO")
        )
        zona = res_zona.scalar_one_or_none()
        if not zona:
            zona = Zona(company_id=company.id, codigo="CENTRO", nombre="Región Centro")
            session.add(zona)
            await session.flush()

        res_vend = await session.execute(
            select(Vendedor).where(Vendedor.company_id == company.id, Vendedor.codigo == "V-01")
        )
        vend = res_vend.scalar_one_or_none()
        if not vend:
            vend = Vendedor(
                company_id=company.id,
                zona_id=zona.id,
                usuario_id=user.id,
                codigo="V-01",
                nombre="Carlos Vendedor",
                telefono="0414-0001122",
                email="carlos@galaxy.test",
                comision_porcentaje=Decimal("3.00"),
            )
            session.add(vend)

        # 5. Categorías
        cat_map: dict[str, Categoria] = {}
        for c_cod, c_nom in [("ALIM", "Alimentos"), ("BEB", "Bebidas")]:
            res_c = await session.execute(
                select(Categoria).where(
                    Categoria.company_id == company.id, Categoria.codigo == c_cod
                )
            )
            cat_obj = res_c.scalar_one_or_none()
            if not cat_obj:
                cat_obj = Categoria(company_id=company.id, codigo=c_cod, nombre=c_nom)
                session.add(cat_obj)
                await session.flush()
            cat_map[c_cod] = cat_obj

        # 6. Alícuotas de IVA
        res_alics = await session.execute(select(AlicuotaIva))
        alicuotas = {a.codigo: a.id for a in res_alics.scalars().all()}
        ali_exento = alicuotas.get("EXENTO")
        ali_general = alicuotas.get("GENERAL")

        # 7. Productos y Carga de Stock
        productos_def = [
            ("HAR-PAN", "Harina de Maíz Pan 1kg", "ALIM", ali_exento, "0.8000", "1.2000"),
            ("ARR-PRI", "Arroz Blanco Primor 1kg", "ALIM", ali_exento, "0.7500", "1.1000"),
            ("REF-COL", "Refresco Cola 2L", "BEB", ali_general, "1.2000", "2.0000"),
            ("ACE-MAZ", "Aceite Vegetal Mazeite 1L", "ALIM", ali_general, "2.1000", "3.0000"),
        ]

        for p_cod, p_desc, c_k, a_id, costo, precio in productos_def:
            res_p = await session.execute(
                select(Product).where(Product.company_id == company.id, Product.codigo == p_cod)
            )
            prod = res_p.scalar_one_or_none()
            if not prod and a_id:
                prod = Product(
                    company_id=company.id,
                    categoria_id=cat_map[c_k].id,
                    alicuota_iva_id=a_id,
                    codigo=p_cod,
                    descripcion=p_desc,
                    unidad="UND",
                    costo_estandar=Decimal(costo),
                    precio_base_usd=Decimal(precio),
                    minimo=Decimal("10.0000"),
                    maximo=Decimal("500.0000"),
                )
                session.add(prod)
                await session.flush()

                # Cargar stock inicial en ambos almacenes
                for wh in (alm_pri, alm_sec):
                    cant = Decimal("100.0000")
                    session.add(
                        StockMovement(
                            company_id=company.id,
                            warehouse_id=wh.id,
                            product_id=prod.id,
                            tipo="CARGO",
                            documento_id=company.id,
                            documento_tipo="INVENTARIO_INICIAL",
                            cantidad=cant,
                            costo_std=Decimal(costo),
                            fecha=hoy(),
                            created_by=user.id,
                        )
                    )
                    session.add(
                        StockBalance(
                            company_id=company.id,
                            warehouse_id=wh.id,
                            product_id=prod.id,
                            cantidad=cant,
                        )
                    )

        # 8. Clientes
        clientes_def = [
            ("J", "20202020-1", "Comercializadora Plaza C.A.", True, Decimal("75.00")),
            ("J", "30303030-2", "Abasto Los Andes S.A.", False, Decimal("0.00")),
        ]
        for tid, ident, nom, ret_iva, porc_iva in clientes_def:
            res_cli = await session.execute(
                select(Cliente).where(
                    Cliente.company_id == company.id, Cliente.identificacion == ident
                )
            )
            if not res_cli.scalar_one_or_none():
                session.add(
                    Cliente(
                        company_id=company.id,
                        tipo_identificacion=tid,
                        identificacion=ident,
                        nombre=nom,
                        direccion="Zona Comercial, Local 1",
                        telefono="0212-5551234",
                        email=f"contacto_{ident}@test.local",
                        nos_retiene_iva=ret_iva,
                        porcentaje_retencion_iva=porc_iva,
                    )
                )

        # 9. Proveedores
        provs_def = [
            ("J-40404040-3", "Distribuidora Polar C.A.", True, Decimal("75.00")),
            ("J-50505050-4", "Servicios Agrícolas C.A.", False, Decimal("0.00")),
        ]
        for rif_p, nom_p, ret_p, porc_p in provs_def:
            res_prov = await session.execute(
                select(Proveedor).where(
                    Proveedor.company_id == company.id, Proveedor.rif == rif_p
                )
            )
            if not res_prov.scalar_one_or_none():
                session.add(
                    Proveedor(
                        company_id=company.id,
                        rif=rif_p,
                        razon_social=nom_p,
                        direccion="Av. Industrial #100",
                        telefono="0241-8889900",
                        retiene_iva=ret_p,
                        porcentaje_retencion_iva=porc_p,
                    )
                )

        # 10. Instrumentos de Pago
        inst_def = [
            ("PAGO-MOVIL", "Pago Móvil Interbancario", "PAGO_MOVIL", "VES"),
            ("TRANS-BS", "Transferencia Bancaria Nacional", "TRANSFERENCIA", "VES"),
            ("EFEC-USD", "Efectivo Dólares USA", "EFECTIVO", "USD"),
            ("ZELLE", "Transferencia Zelle", "TRANSFERENCIA", "USD"),
        ]
        for cod_i, nom_i, tipo_i, mon_i in inst_def:
            res_i = await session.execute(
                select(InstrumentoPago).where(
                    InstrumentoPago.company_id == company.id, InstrumentoPago.codigo == cod_i
                )
            )
            if not res_i.scalar_one_or_none():
                session.add(
                    InstrumentoPago(
                        company_id=company.id,
                        codigo=cod_i,
                        nombre=nom_i,
                        tipo=tipo_i,
                        moneda=mon_i,
                    )
                )

        # 11. Cuentas Bancarias
        bancos_def = [
            ("0134-BANESCO-VES", "Banesco Banco Universal (Bs.)", "VES", Decimal("150000.00")),
            ("0134-CUSTODIA-USD", "Banesco Cuenta Custodia ($)", "USD", Decimal("5000.00")),
        ]
        for num_b, nom_b, mon_b, saldo_b in bancos_def:
            res_b = await session.execute(
                select(CuentaBancaria).where(
                    CuentaBancaria.company_id == company.id,
                    CuentaBancaria.numero_cuenta == num_b,
                )
            )
            if not res_b.scalar_one_or_none():
                session.add(
                    CuentaBancaria(
                        company_id=company.id,
                        numero_cuenta=num_b,
                        banco_nombre=nom_b,
                        moneda=mon_b,
                        saldo_actual=saldo_b,
                        activa=True,
                    )
                )

        await session.commit()

    await engine.dispose()
    return tenant
