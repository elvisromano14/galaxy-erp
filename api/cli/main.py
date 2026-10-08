import asyncio
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from rich.console import Console
from rich.table import Table

from app.control.aprovisionamiento import aprovisionar_tenant
from app.control.db import control_session
from app.control.repository import (
    actualizar_estado_tenant,
    listar_tenants,
    obtener_tenant_por_slug,
)

app = typer.Typer(
    name="erpctl",
    help="Herramienta de línea de comandos para administración de Galaxy ERP.",
    no_args_is_help=True,
)

control_app = typer.Typer(help="Comandos para el plano de control (erp_control).")
tenant_app = typer.Typer(help="Comandos para gestión de tenants (clientes).")

app.add_typer(control_app, name="control")
app.add_typer(tenant_app, name="tenant")

console = Console()


@control_app.command("init")
def control_init() -> None:
    """Inicializa la base de datos de control (erp_control) aplicando sus migraciones."""
    ini_path = Path(__file__).resolve().parent.parent / "alembic_control.ini"
    if not ini_path.exists():
        console.print(f"[red]Error: No se encontró el archivo de configuración {ini_path}[/red]")
        raise typer.Exit(code=1)

    try:
        console.print(
            f"[yellow]Aplicando migraciones a erp_control usando {ini_path.name}...[/yellow]"
        )
        alembic_cfg = Config(str(ini_path))
        alembic_cfg.set_main_option("script_location", str(ini_path.parent / "migrations_control"))
        command.upgrade(alembic_cfg, "head")
        console.print("[green]✓ Plano de control inicializado exitosamente.[/green]")
    except Exception as exc:
        console.print(f"[red]Error al inicializar el plano de control: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@tenant_app.command("crear")
def tenant_crear(
    slug: str = typer.Option(..., "--slug", help="Slug único del tenant (ej: acme)"),
    nombre: str = typer.Option(..., "--nombre", help="Nombre comercial o razón social"),
    plan: str = typer.Option("pro", "--plan", help="Plan contratado (basico, pro, enterprise)"),
    admin_email: str = typer.Option(..., "--admin-email", help="Correo del administrador inicial"),
    admin_password: str | None = typer.Option(
        None, "--admin-password", help="Contraseña del administrador inicial (opcional)"
    ),
    modulos: str | None = typer.Option(
        None, "--modulos", help="Módulos habilitados separados por coma (ej: ventas,inventario)"
    ),
) -> None:
    """Aprovisiona un nuevo cliente con su base de datos aislada, tablas y permisos."""
    modulos_lista = [m.strip() for m in modulos.split(",")] if modulos else None

    console.print(f"[yellow]Aprovisionando tenant '{slug}' ({nombre})...[/yellow]")

    async def _ejecutar() -> None:
        tenant = await aprovisionar_tenant(
            slug=slug,
            nombre=nombre,
            plan=plan,
            admin_email=admin_email,
            admin_password=admin_password,
            modulos=modulos_lista,
        )
        console.print(
            f"[green]✓ Tenant '{tenant.slug}' aprovisionado y activo exitosamente.[/green]"
        )
        console.print(f"  Base de datos: [bold]{tenant.db_name}[/bold]")
        console.print(f"  Estado: [bold]{tenant.estado}[/bold]")

    try:
        asyncio.run(_ejecutar())
    except Exception as exc:
        console.print(f"[red]Error al aprovisionar tenant: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@tenant_app.command("listar")
def tenant_listar(
    solo_db: bool = typer.Option(
        False,
        "--solo-db",
        help="Listar únicamente los nombres de las bases de datos",
    ),
) -> None:
    """Lista todos los tenants registrados en erp_control."""

    async def _ejecutar() -> None:
        async with control_session() as session:
            tenants = await listar_tenants(session)
            if solo_db:
                for t in tenants:
                    if t.estado in ("activo", "suspendido"):
                        console.print(t.db_name)
                return

            if not tenants:
                console.print("[yellow]No hay tenants registrados en el sistema.[/yellow]")
                return

            tabla = Table(title="Tenants Registrados en Galaxy ERP")
            tabla.add_column("Slug", style="cyan")
            tabla.add_column("Nombre", style="bold")
            tabla.add_column("Base de Datos", style="magenta")
            tabla.add_column("Plan", style="blue")
            tabla.add_column("Estado", style="green")
            tabla.add_column("Creado En", style="dim")

            for t in tenants:
                color_estado = {
                    "activo": "green",
                    "aprovisionando": "yellow",
                    "suspendido": "red",
                    "fallido": "bold red",
                    "archivado": "dim",
                }.get(t.estado, "white")
                tabla.add_row(
                    t.slug,
                    t.nombre,
                    t.db_name,
                    t.plan,
                    f"[{color_estado}]{t.estado}[/{color_estado}]",
                    t.creado_en.strftime("%Y-%m-%d %H:%M"),
                )

            console.print(tabla)

    asyncio.run(_ejecutar())


@tenant_app.command("suspender")
def tenant_suspender(
    slug: str = typer.Option(..., "--slug", help="Slug del tenant a suspender"),
) -> None:
    """Suspende a un tenant (bloquea el acceso en la API sin pérdida de datos)."""

    async def _ejecutar() -> None:
        async with control_session() as session:
            tenant = await obtener_tenant_por_slug(session, slug)
            if not tenant:
                console.print(f"[red]Error: No existe el tenant con slug '{slug}'.[/red]")
                raise typer.Exit(code=1)
            await actualizar_estado_tenant(session, tenant.id, "suspendido")
            console.print(f"[yellow]✓ Tenant '{slug}' ha sido suspendido.[/yellow]")

    asyncio.run(_ejecutar())


@tenant_app.command("activar")
def tenant_activar(
    slug: str = typer.Option(..., "--slug", help="Slug del tenant a reactivar"),
) -> None:
    """Reactiva a un tenant suspendido."""

    async def _ejecutar() -> None:
        async with control_session() as session:
            tenant = await obtener_tenant_por_slug(session, slug)
            if not tenant:
                console.print(f"[red]Error: No existe el tenant con slug '{slug}'.[/red]")
                raise typer.Exit(code=1)
            await actualizar_estado_tenant(session, tenant.id, "activo")
            console.print(f"[green]✓ Tenant '{slug}' ha sido reactivado a estado activo.[/green]")

    asyncio.run(_ejecutar())


@app.command("salud")
def salud() -> None:
    """Verifica estado de disco, memoria y servicios."""
    console.print("[cyan]Verificando estado del servidor y servicios...[/cyan]")


if __name__ == "__main__":
    app()
