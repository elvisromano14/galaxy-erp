import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.control.db import control_session
from app.control.models import Tenant
from app.control.repository import (
    actualizar_estado_tenant,
    crear_tenant,
    finalizar_job,
    obtener_tenant_por_slug,
    registrar_job,
)
from app.core.config import settings
from app.core.errores import GalaxyERPException
from app.core.seguridad import hashear_password
from app.modules.admin.models import AlicuotaIva, Company, Warehouse
from app.modules.identidad.models import Permiso, Rol, RolPermiso, Usuario, UsuarioRol

SLUG_REGEX = re.compile(r"^[a-z][a-z0-9-]{1,38}[a-z0-9]$")

PERMISOS_BASE = [
    # Admin
    ("admin.empresa.editar", "admin", "Editar información de la empresa"),
    ("admin.usuario.crear", "admin", "Crear usuarios en la empresa"),
    ("admin.usuario.editar", "admin", "Editar usuarios y permisos"),
    ("admin.rol.administrar", "admin", "Gestionar roles"),
    # Inventario
    ("inventario.ver", "inventario", "Visualizar inventario y catálogo"),
    ("inventario.cargo.crear", "inventario", "Registrar cargos de stock"),
    ("inventario.descargo.crear", "inventario", "Registrar descargos de stock"),
    ("inventario.ajuste.aprobar", "inventario", "Aprobar ajustes de inventario"),
    ("inventario.traslado.crear", "inventario", "Registrar traslados entre depósitos"),
    ("inventario.precio.cambiar", "inventario", "Modificar listas de precios"),
    # Ventas
    ("ventas.pedido.crear", "ventas", "Crear pedidos de venta"),
    ("ventas.factura.crear", "ventas", "Crear facturas de venta"),
    ("ventas.factura.aprobar", "ventas", "Aprobar y emitir facturas"),
    ("ventas.factura.anular", "ventas", "Anular facturas de venta"),
    # Compras
    ("compras.orden.crear", "compras", "Crear órdenes de compra"),
    ("compras.compra.crear", "compras", "Registrar compras de mercancía"),
    ("compras.compra.aprobar", "compras", "Aprobar compras"),
    # Bancos y Finanzas
    ("bancos.transaccion.crear", "bancos", "Registrar transacciones bancarias"),
    ("bancos.conciliacion.crear", "bancos", "Realizar conciliaciones"),
    ("cxc.cobro.crear", "cxc_cxp", "Registrar cobros a clientes"),
    ("cxp.pago.crear", "cxc_cxp", "Registrar pagos a proveedores"),
    # Impuestos
    ("impuestos.libros.ver", "impuestos", "Consultar libros de compras y ventas"),
    ("impuestos.alicuotas.editar", "impuestos", "Administrar alícuotas y retenciones"),
    # Reportes
    ("reportes.ver", "reportes", "Consultar reportes"),
    ("reportes.exportar", "reportes", "Exportar reportes a PDF/Excel/CSV"),
]

ALICUOTAS_BASE = [
    ("GENERAL", Decimal("16.00"), "Gaceta Oficial N° 6.507"),
    ("REDUCIDA", Decimal("8.00"), "Gaceta Oficial N° 6.507"),
    ("ADICIONAL", Decimal("31.00"), "Gaceta Oficial N° 6.507"),
    ("EXENTO", Decimal("0.00"), "Ley de Impuesto al Valor Agregado"),
]


def _extraer_url_servidor(url_completa: str, nueva_db: str) -> str:
    """Reemplaza el nombre de la base de datos en la URL de conexión."""
    partes = url_completa.rsplit("/", 1)
    return f"{partes[0]}/{nueva_db}"


async def aprovisionar_tenant(
    *,
    slug: str,
    nombre: str,
    plan: str,
    admin_email: str,
    admin_password: str | None = None,
    admin_nombre: str = "Administrador Principal",
    empresa_rif: str | None = None,
    empresa_razon_social: str | None = None,
    modulos: list[str] | None = None,
    db_host: str = "127.0.0.1",
    db_port: int = 5432,
    es_canario: bool = False,
) -> Tenant:
    # 1. Validar slug
    if not SLUG_REGEX.match(slug):
        raise GalaxyERPException(
            code="SLUG_INVALIDO",
            title="Slug inválido",
            status=400,
            detail=f"El slug '{slug}' no cumple con el formato requerido.",
        )

    db_name = f"erp_c_{slug}"
    modulos_lista = modulos or [
        "admin",
        "identidad",
        "inventario",
        "ventas",
        "compras",
        "bancos",
        "cxc_cxp",
        "impuestos",
        "reportes",
    ]

    async with control_session() as c_session:
        existente = await obtener_tenant_por_slug(c_session, slug)
        if existente:
            raise GalaxyERPException(
                code="TENANT_YA_EXISTE",
                title="Tenant existente",
                status=409,
                detail=f"Ya existe un tenant con el slug '{slug}'.",
            )

        # 2. Registrar en erp_control en estado aprovisionando
        tenant = await crear_tenant(
            c_session,
            slug=slug,
            nombre=nombre,
            plan=plan,
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            es_canario=es_canario,
            modulos=modulos_lista,
        )

        job = await registrar_job(
            c_session,
            tenant_id=tenant.id,
            tipo="CREAR",
            estado="EN_CURSO",
            detalle={"slug": slug, "db_name": db_name, "plan": plan},
        )

    tenant_id = tenant.id
    job_id = job.id

    try:
        # 3. Crear base física con erp_owner
        url_server = _extraer_url_servidor(settings.CONTROL_DB_OWNER_URL, "postgres")
        engine_server = create_async_engine(url_server, isolation_level="AUTOCOMMIT")

        async with engine_server.connect() as conn:
            # Validar si existe la base antes de crearla
            db_check = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            if not db_check.scalar():
                await conn.execute(text(f'CREATE DATABASE "{db_name}" OWNER erp_owner'))
                await conn.execute(text(f'REVOKE CONNECT ON DATABASE "{db_name}" FROM PUBLIC'))
                await conn.execute(text(f'GRANT CONNECT ON DATABASE "{db_name}" TO erp_app'))
        await engine_server.dispose()

        # 4. Migrar hasta head con Alembic
        tenant_owner_url = _extraer_url_servidor(settings.CONTROL_DB_OWNER_URL, db_name)
        alembic_ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(alembic_ini_path.parent / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", tenant_owner_url)

        # Ejecutar upgrade
        command.upgrade(alembic_cfg, "head")

        # 5. Permisos para erp_app en la nueva base
        engine_tenant_owner = create_async_engine(tenant_owner_url)
        async with engine_tenant_owner.begin() as conn:
            await conn.execute(text("GRANT USAGE ON SCHEMA public TO erp_app"))
            await conn.execute(
                text(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO erp_app"
                )
            )
            await conn.execute(
                text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO erp_app")
            )
            await conn.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE erp_owner IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO erp_app"
                )
            )
            await conn.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE erp_owner IN SCHEMA public "
                    "GRANT USAGE, SELECT ON SEQUENCES TO erp_app"
                )
            )
            # Auditoría append-only para erp_app
            await conn.execute(text("REVOKE UPDATE, DELETE ON audit_log FROM erp_app"))

        # 6 y 7. Sembrar datos base y crear primera empresa y admin
        pwd_hash = hashear_password(admin_password or "Admin123456!")
        rif = empresa_rif or f"J-{slug.upper()[:8]}001"
        razon_social = empresa_razon_social or nombre

        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(engine_tenant_owner) as t_session:
            # 6.1 Permisos
            permisos_objs: list[Permiso] = []
            for codigo, mod, desc in PERMISOS_BASE:
                p = Permiso(codigo=codigo, modulo=mod, descripcion=desc)
                t_session.add(p)
                permisos_objs.append(p)
            await t_session.flush()

            # 6.2 Alícuotas
            for cod, porc, fuente in ALICUOTAS_BASE:
                al = AlicuotaIva(
                    codigo=cod,
                    porcentaje=porc,
                    vigente_desde=date(2020, 1, 1),
                    fuente=fuente,
                )
                t_session.add(al)

            # 7.1 Empresa
            company = Company(
                rif=rif,
                razon_social=razon_social,
                contribuyente="ORDINARIO",
                moneda_base="VES",
            )
            t_session.add(company)
            await t_session.flush()

            # 7.2 Depósito por defecto
            deposito = Warehouse(
                company_id=company.id,
                codigo="PRINCIPAL",
                nombre="Depósito Principal",
            )
            t_session.add(deposito)

            # 6.3 Roles
            rol_admin = Rol(
                company_id=company.id,
                codigo="administrador",
                nombre="Administrador",
                descripcion="Acceso total al sistema",
                es_sistema=True,
            )
            t_session.add(rol_admin)
            await t_session.flush()

            for p in permisos_objs:
                t_session.add(RolPermiso(rol_id=rol_admin.id, permiso_codigo=p.codigo))

            # 7.3 Primer Administrador
            admin_user = Usuario(
                company_id=company.id,
                email=admin_email,
                username="admin",
                password_hash=pwd_hash,
                nombre_completo=admin_nombre,
            )
            t_session.add(admin_user)
            await t_session.flush()

            t_session.add(UsuarioRol(usuario_id=admin_user.id, rol_id=rol_admin.id))
            await t_session.commit()

        await engine_tenant_owner.dispose()

        # 8 y 9. Verificar conexión con erp_app
        tenant_app_url = _extraer_url_servidor(settings.CONTROL_DB_URL, db_name)
        engine_tenant_app = create_async_engine(
            tenant_app_url,
            connect_args={"statement_cache_size": 0},
        )
        async with engine_tenant_app.connect() as conn:
            res = await conn.execute(text("SELECT count(*) FROM company"))
            conteo = res.scalar()
            if conteo != 1:
                raise RuntimeError("Verificación de empresa fallida.")
        await engine_tenant_app.dispose()

        # 10. Activar tenant en erp_control
        async with control_session() as c_session:
            tenant_activo = await actualizar_estado_tenant(c_session, tenant_id, "activo")
            await finalizar_job(
                c_session,
                job_id,
                estado="OK",
                detalle={"mensaje": "Aprovisionamiento exitoso", "db_name": db_name},
            )
            assert tenant_activo is not None
            return tenant_activo

    except Exception as exc:
        async with control_session() as c_session:
            await actualizar_estado_tenant(c_session, tenant_id, "fallido")
            await finalizar_job(
                c_session,
                job_id,
                estado="ERROR",
                detalle={"error": str(exc)},
            )
        raise exc
