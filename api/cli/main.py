import typer
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
    """Inicializa la base de datos de control (erp_control)."""
    console.print("[yellow]Inicializando base de control erp_control...[/yellow]")
    # Se implementará en la siguiente etapa de Fase 0


@tenant_app.command("listar")
def tenant_listar(
    solo_db: bool = typer.Option(
        False, "--solo-db", help="Listar únicamente los nombres de las bases de datos"
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
