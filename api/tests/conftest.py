from collections.abc import AsyncGenerator

import pytest

from app.control.db import close_control_engines


@pytest.fixture(scope="session", autouse=True)
async def limpiar_conexiones_bd() -> AsyncGenerator[None, None]:
    yield
    await close_control_engines()
