import httpx
import pytest

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_cabeceras_de_seguridad_http() -> None:
    """Verifica que las cabeceras de endurecimiento se inyecten correctamente."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/salud")
        assert resp.status_code == 200

        headers = resp.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "server" not in headers
        assert "x-powered-by" not in headers


@pytest.mark.asyncio
async def test_rechazo_payload_excesivo() -> None:
    """Verifica que peticiones con Content-Length mayor al límite sean rechazadas con 413."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Simulamos una cabecera de tamaño mayor que MAX_BODY_SIZE_MB
        tamano_excesivo = (settings.MAX_BODY_SIZE_MB * 1024 * 1024) + 1000
        headers = {"content-length": str(tamano_excesivo)}
        resp = await client.post("/api/v1/auth/login", headers=headers, json={})
        assert resp.status_code == 413
        assert resp.json()["code"] == "PAYLOAD_TOO_LARGE"
