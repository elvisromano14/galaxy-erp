import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from rich.console import Console
from rich.table import Table
from sqlalchemy.ext.asyncio import create_async_engine

from app.control.db import control_session
from app.control.models import Tenant
from app.control.repository import (
    finalizar_job,
    listar_tenants,
    registrar_job,
)
from app.core.config import settings

console = Console()

_ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


def _build_tenant_owner_url(tenant: Tenant) -> str:
    """URL directa (puerto 5432, erp_owner) para aplicar migraciones."""
    partes = settings.CONTROL_DB_OWNER_URL.rsplit("/", 1)
    return f"{partes[0]}/{tenant.db_name}"


def _migrar_tenant(tenant: Tenant) -> str | None:
    """Ejecuta upgrade head para un tenant. Devuelve la revisión head o None si falló."""
    tenant_url = _build_tenant_owner_url(tenant)
    alembic_cfg = Config(str(_ALEMBIC_INI))
    alembic_cfg.set_main_option("script_location", str(_ALEMBIC_INI.parent / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", tenant_url)
    command.upgrade(alembic_cfg, "head")
    # Obtener revisión aplicada
    from sqlalchemy import text

    async def _get_rev() -> str | None:
        engine = create_async_engine(tenant_url)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = res.fetchone()
        await engine.dispose()
        return str(row[0]) if row else None

    return asyncio.run(_get_rev())


async def migrar_todos(solo_slug: str | None = None) -> None:
    """Orquesta migraciones sobre clientes activos/suspendidos. Canario primero."""
    async with control_session() as session:
        todos = await listar_tenants(session)

    if solo_slug:
        tenants_destino = [t for t in todos if t.slug == solo_slug]
        if not tenants_destino:
            console.print(f"[red]No se encontró ningún tenant con slug '{solo_slug}'.[/red]")
            return
    else:
        tenants_destino = [t for t in todos if t.estado in ("activo", "suspendido")]

    # Ordenar: canarios primero
    tenants_destino.sort(key=lambda t: (0 if t.es_canario else 1, t.creado_en))

    migrados: list[str] = []
    fallidos: list[tuple[str, str]] = []
    omitidos: list[str] = []

    for tenant in tenants_destino:
        if tenant.estado not in ("activo", "suspendido"):
            omitidos.append(tenant.slug)
            continue

        canario_label = " [bold yellow][canario][/bold yellow]" if tenant.es_canario else ""
        console.print(f"\n→ Migrando {tenant.slug}{canario_label}  ({tenant.db_name})")

        async with control_session() as session:
            job = await registrar_job(
                session,
                tenant_id=tenant.id,
                tipo="MIGRAR",
                estado="EN_CURSO",
                detalle={"db_name": tenant.db_name},
            )

        try:
            nueva_rev = _migrar_tenant(tenant)
            async with control_session() as session:
                await finalizar_job(
                    session,
                    job.id,
                    estado="OK",
                    detalle={"schema_rev": nueva_rev},
                )
                # Actualizar schema_rev en el tenant
                from sqlalchemy import update

                from app.control.db import get_control_session_factory
                from app.control.models import Tenant as TenantModel

                factory = get_control_session_factory()
                async with factory() as s:
                    await s.execute(
                        update(TenantModel)
                        .where(TenantModel.id == tenant.id)
                        .values(schema_rev=nueva_rev),
                    )
                    await s.commit()

            console.print(f"  [green]✓ OK — revisión: {nueva_rev}[/green]")
            migrados.append(tenant.slug)

        except Exception as exc:  # noqa: BLE001
            async with control_session() as session:
                await finalizar_job(
                    session,
                    job.id,
                    estado="ERROR",
                    detalle={"error": str(exc)},
                )
            console.print(f"  [red]✗ ERROR: {exc}[/red]")
            fallidos.append((tenant.slug, str(exc)))

            if tenant.es_canario:
                console.print(
                    "[bold red]Migración del canario falló. "
                    "Se detiene el proceso para evitar daños en producción.[/bold red]"
                )
                break

    # Reporte final
    tabla = Table(title="Reporte de Migraciones")
    tabla.add_column("Estado")
    tabla.add_column("Slugs")
    tabla.add_row("[green]Migrados[/green]", ", ".join(migrados) or "—")
    tabla.add_row("[red]Fallidos[/red]", ", ".join(s for s, _ in fallidos) or "—")
    tabla.add_row("[dim]Omitidos[/dim]", ", ".join(omitidos) or "—")
    console.print(tabla)
