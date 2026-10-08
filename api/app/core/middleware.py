"""Middlewares y utilidades de endurecimiento (hardening) de seguridad HTTP."""

from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.errores import GalaxyERPException


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inyecta cabeceras HTTP de seguridad estrictas (Defense in Depth)."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        response: Response = await call_next(request)

        if settings.ENABLE_SECURITY_HEADERS:
            headers = response.headers
            headers["X-Content-Type-Options"] = "nosniff"
            headers["X-Frame-Options"] = "DENY"
            headers["X-XSS-Protection"] = "1; mode=block"
            headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            headers["Permissions-Policy"] = (
                "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
            )

            # HSTS solo en conexiones HTTPS o entornos de producción
            if request.url.scheme == "https" or settings.ENVIRONMENT == "production":
                headers["Strict-Transport-Security"] = (
                    "max-age=63072000; includeSubDomains; preload"
                )

            # CSP restrictivo que permite Swagger UI en desarrollo pero bloquea inyecciones
            if not request.url.path.startswith("/docs") and not request.url.path.startswith(
                "/openapi.json"
            ):
                headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "img-src 'self' data: blob:; "
                    "style-src 'self' 'unsafe-inline'; "
                    "script-src 'self'; "
                    "frame-ancestors 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self';"
                )

            # Ocultar huellas de servidor
            if "Server" in headers:
                del headers["Server"]
            if "X-Powered-By" in headers:
                del headers["X-Powered-By"]

        return response


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Rechaza peticiones con cuerpos que excedan el límite de tamaño permitido."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        max_bytes = settings.MAX_BODY_SIZE_MB * 1024 * 1024
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                length = int(content_length)
                if length > max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "type": "https://galaxyerp.local/errores/payload-too-large",
                            "title": "Cuerpo de petición excesivo",
                            "status": 413,
                            "detail": (
                                f"El tamaño de la petición ({length} bytes) "
                                f"excede el máximo permitido ({max_bytes} bytes)."
                            ),
                            "code": "PAYLOAD_TOO_LARGE",
                        },
                        media_type="application/problem+json",
                    )
            except ValueError:
                pass

        return await call_next(request)


async def verificar_rate_limit_login(request: Request) -> None:
    """Valida rate limiting por IP para mitigar ataques de fuerza bruta en login."""
    client_ip = request.client.host if request.client else "unknown"

    # Si estamos en pruebas unitarias/locales sin IP, omitir
    if client_ip in ("testclient", "unknown") and settings.ENVIRONMENT == "development":
        return

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"rate_limit:login:{client_ip}"
        intentos = await r.incr(key)
        if intentos == 1:
            await r.expire(key, settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS)
        await r.aclose()

        if intentos > settings.RATE_LIMIT_LOGIN_MAX:
            msg = (
                f"Ha superado el límite de {settings.RATE_LIMIT_LOGIN_MAX} intentos/min. "
                "Por seguridad, espere antes de reintentar."
            )
            raise GalaxyERPException(
                code="RATE_LIMIT_EXCEDIDO",
                title="Demasiados intentos de acceso",
                status=429,
                detail=msg,
            )
    except GalaxyERPException:
        raise
    except Exception:
        # Falla-segura abierta ante caída de Redis para no bloquear tráfico legítimo
        pass
