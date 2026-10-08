"""Punto de entrada para el worker y planificador de tareas en segundo plano.

Ejecutado en contenedor dedicado según Quadlet worker.container:
    python -m app.workers.main
"""

import asyncio
import signal
import sys
from typing import Any

import structlog
from redis.asyncio import Redis

from app.core.config import settings

logger = structlog.get_logger()


async def check_redis_connection() -> bool:
    """Verifica que Redis esté disponible antes de iniciar colas."""
    try:
        r = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose()
        return True
    except Exception as exc:
        logger.warning("No se pudo conectar a Redis", error=str(exc))
        return False


async def run_worker() -> None:
    """Bucle principal de ejecución del worker."""
    logger.info("Iniciando Galaxy ERP Background Worker...", app_name=settings.APP_NAME)

    redis_ok = await check_redis_connection()
    if redis_ok:
        logger.info("✓ Conexión con Redis establecida correctamente.")
    else:
        logger.warning("⚠ Redis no disponible. El worker operará en modo espera.")

    stop_event = asyncio.Event()

    def _signal_handler(*_: Any) -> None:
        logger.info("Señal de parada recibida. Deteniendo worker ordenadamente...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Fallback en plataformas sin soporte de loop.add_signal_handler
            signal.signal(sig, lambda *_: stop_event.set())

    logger.info("Worker listo y escuchando tareas en segundo plano.")

    # Bucle de liveness y ejecución de planificador
    try:
        while not stop_event.is_set():
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Bucle de worker cancelado.")
    finally:
        logger.info("Galaxy ERP Background Worker finalizado.")


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
