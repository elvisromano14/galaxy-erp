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


@app.command("migrar")
def migrar(
    todos: bool = typer.Option(
        False, "--todos", help="Migrar todos los clientes activos/suspendidos"
    ),
    slug: str | None = typer.Option(None, "--slug", help="Migrar únicamente el cliente indicado"),
) -> None:
    """Aplica migraciones Alembic a clientes. Canario primero. Falla segura."""
    from app.control.migraciones import migrar_todos

    if not todos and not slug:
        console.print("[red]Debes indicar --todos o --slug <slug>.[/red]")
        raise typer.Exit(code=1)

    asyncio.run(migrar_todos(solo_slug=slug))


@app.command("salud")
def salud() -> None:
    """Verifica estado de disco, memoria y conectividad de servicios."""
    import shutil

    from redis.asyncio import Redis
    from sqlalchemy import text

    console.print("[cyan]Verificando estado del servidor y servicios...[/cyan]\n")

    tabla = Table(title="Estado del Sistema - Galaxy ERP")
    tabla.add_column("Componente", style="bold")
    tabla.add_column("Detalle")
    tabla.add_column("Estado")

    # 1. Espacio en disco
    total, used, free = shutil.disk_usage("/")
    total_gb = total / (1024**3)
    free_gb = free / (1024**3)
    used_pct = (used / total) * 100
    color_disco = "green" if used_pct < 80 else ("yellow" if used_pct < 90 else "red")
    tabla.add_row(
        "Almacenamiento (Disco /)",
        f"{used_pct:.1f}% usado (Libre: {free_gb:.1f} GB de {total_gb:.1f} GB)",
        f"[{color_disco}]OK[/{color_disco}]"
        if used_pct < 90
        else f"[{color_disco}]ALERTA[/{color_disco}]",
    )

    # 2. Memoria RAM
    mem_detalle = "N/A"
    mem_estado = "[green]OK[/green]"
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem_info = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                mem_info[parts[0].strip()] = parts[1].strip()
        total_kb = int(mem_info.get("MemTotal", "0 kB").split()[0])
        avail_kb = int(mem_info.get("MemAvailable", "0 kB").split()[0])
        if total_kb > 0:
            total_mb = total_kb / 1024
            avail_mb = avail_kb / 1024
            used_pct_mem = ((total_kb - avail_kb) / total_kb) * 100
            mem_detalle = (
                f"{used_pct_mem:.1f}% usada (Disponible: {avail_mb:.0f} MB de {total_mb:.0f} MB)"
            )
            mem_estado = "[green]OK[/green]" if used_pct_mem < 85 else "[yellow]ALTO[/yellow]"
    except Exception:
        mem_detalle = "No disponible"

    tabla.add_row("Memoria RAM", mem_detalle, mem_estado)

    # 3. Base de Datos Control y Redis
    async def _verificar_servicios() -> tuple[bool, str, bool, str]:
        pg_ok, pg_err = False, ""
        try:
            from app.control.db import get_control_owner_engine

            engine = get_control_owner_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            pg_ok = True
        except Exception as exc:
            pg_err = str(exc)

        redis_ok, redis_err = False, ""
        try:
            from app.core.config import settings

            r = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.ping()
            await r.aclose()
            redis_ok = True
        except Exception as exc:
            redis_err = str(exc)

        return pg_ok, pg_err, redis_ok, redis_err

    pg_ok, pg_err, redis_ok, redis_err = asyncio.run(_verificar_servicios())

    tabla.add_row(
        "PostgreSQL (Control DB)",
        "Conexión activa a erp_control" if pg_ok else f"Fallo: {pg_err[:50]}...",
        "[green]OK[/green]" if pg_ok else "[red]DESCONECTADO[/red]",
    )

    tabla.add_row(
        "Redis",
        "Conexión y PING exitoso" if redis_ok else f"Fallo: {redis_err[:50]}...",
        "[green]OK[/green]" if redis_ok else "[yellow]DESCONECTADO[/yellow]",
    )

    console.print(tabla)


if __name__ == "__main__":
    app()
