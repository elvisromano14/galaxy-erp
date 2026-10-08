import uuid
from collections import OrderedDict
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.control.models import Tenant
from app.core.config import settings


def _password_app_por_defecto() -> str:
    """Extrae la contraseña de erp_app desde la URL de control configurada en settings."""
    try:
        url_limpia = settings.CONTROL_DB_URL.replace("postgresql+asyncpg://", "http://")
        parsed = urlparse(url_limpia)
        if parsed.password:
            return parsed.password
    except Exception:
        pass
    return "erp_app_pass"


class MotoresDeClientes:
    """Caché LRU de motores SQLAlchemy (AsyncEngine) por tenant."""

    def __init__(self, maximo: int = 20):
        self._cache: OrderedDict[str, AsyncEngine] = OrderedDict()
        self._max = maximo

    async def obtener(self, tenant: Tenant, password_app: str | None = None) -> AsyncEngine:
        clave = str(tenant.id)
        if clave in self._cache:
            self._cache.move_to_end(clave)
            return self._cache[clave]

        # Conexión con rol erp_app (apunta a PgBouncer / PostgreSQL con statement_cache_size=0)
        pwd = password_app or _password_app_por_defecto()
        url = tenant.url_app(usuario="erp_app", password=pwd)
        motor = create_async_engine(
            url,
            pool_size=3,
            max_overflow=2,
            pool_pre_ping=True,
            connect_args={"statement_cache_size": 0},
        )
        self._cache[clave] = motor

        if len(self._cache) > self._max:
            _, viejo = self._cache.popitem(last=False)
            await viejo.dispose()

        return motor

    async def liberar_tenant(self, tenant_id: uuid.UUID) -> None:
        clave = str(tenant_id)
        if clave in self._cache:
            motor = self._cache.pop(clave)
            await motor.dispose()

    async def cerrar_todos(self) -> None:
        for motor in self._cache.values():
            await motor.dispose()
        self._cache.clear()


_gestor_motores: MotoresDeClientes | None = None


def get_gestor_motores() -> MotoresDeClientes:
    global _gestor_motores
    if _gestor_motores is None:
        _gestor_motores = MotoresDeClientes()
    return _gestor_motores
