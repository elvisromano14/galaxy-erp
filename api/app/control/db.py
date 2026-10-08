from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_control_engine: AsyncEngine | None = None
_control_owner_engine: AsyncEngine | None = None
_control_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_control_engine() -> AsyncEngine:
    global _control_engine
    if _control_engine is None:
        _control_engine = create_async_engine(
            settings.CONTROL_DB_URL,
            pool_pre_ping=True,
            connect_args={"statement_cache_size": 0},  # PgBouncer transaction mode
        )
    return _control_engine


def get_control_owner_engine() -> AsyncEngine:
    global _control_owner_engine
    if _control_owner_engine is None:
        _control_owner_engine = create_async_engine(
            settings.CONTROL_DB_OWNER_URL,
            pool_pre_ping=True,
        )
    return _control_owner_engine


def get_control_session_factory() -> async_sessionmaker[AsyncSession]:
    global _control_session_factory
    if _control_session_factory is None:
        _control_session_factory = async_sessionmaker(
            bind=get_control_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _control_session_factory


@asynccontextmanager
async def control_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_control_session_factory()
    async with factory() as session:
        yield session


async def close_control_engines() -> None:
    global _control_engine, _control_owner_engine, _control_session_factory
    if _control_engine is not None:
        await _control_engine.dispose()
        _control_engine = None
    if _control_owner_engine is not None:
        await _control_owner_engine.dispose()
        _control_owner_engine = None
    _control_session_factory = None
