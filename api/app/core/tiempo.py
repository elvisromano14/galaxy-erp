from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

CARACAS_TZ = ZoneInfo(settings.TIMEZONE)


def ahora() -> datetime:
    """Retorna la fecha y hora actual en la zona horaria de Venezuela."""
    return datetime.now(CARACAS_TZ)


def hoy() -> date:
    """Retorna la fecha actual en la zona horaria de Venezuela."""
    return ahora().date()


def a_caracas(dt: datetime) -> datetime:
    """Convierte cualquier datetime a la zona horaria de Venezuela."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=CARACAS_TZ)
    return dt.astimezone(CARACAS_TZ)
