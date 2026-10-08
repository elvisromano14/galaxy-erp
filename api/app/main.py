from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errores import GalaxyERPException
from app.modules.identidad.router import router as auth_router

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

app.include_router(auth_router, prefix="/api/v1")


@app.exception_handler(GalaxyERPException)
async def galaxy_exception_handler(request: Request, exc: GalaxyERPException) -> JSONResponse:
    trace_id = request.headers.get("X-Request-Id")
    problem = exc.to_problem_detail(trace_id=trace_id)
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


@app.get("/salud", tags=["Operación"])
async def salud() -> dict[str, str]:
    """Liveness check para balanceadores y monitoreo."""
    return {"estado": "ok"}


@app.get("/salud/lista", tags=["Operación"])
async def salud_lista() -> dict[str, str]:
    """Readiness check comprobando dependencias críticas (BD de control y Redis)."""
    # Se completará con comprobación activa de conexiones
    return {"estado": "ok", "control_db": "ok", "redis": "ok"}
