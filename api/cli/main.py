from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from rich.console import Console

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


@tenant_app.command("listar")
def tenant_listar(
    solo_db: bool = typer.Option(
        False,
        "--solo-db",
        help="Listar únicamente los nombres de las bases de datos",
    ),
) -> None:
    """Lista todos los tenants registrados en erp_control."""
    console.print("[green]Listado de tenants registrados[/green]")


@app.command("salud")
def salud() -> None:
    """Verifica estado de disco, memoria y servicios."""
    console.print("[cyan]Verificando estado del servidor y servicios...[/cyan]")


if __name__ == "__main__":
    app()
