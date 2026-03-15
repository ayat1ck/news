"""Async database session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.config import get_settings

settings = get_settings()

# Синхронный движок для старта приложения (ожидание БД, create_all, сиды) — на Windows + Docker
# Явно UTF-8, иначе ответы сервера дают 'utf-8' codec can't decode (локаль/консоль)
_sync_connect_args = {"options": "-c client_encoding=UTF8"}
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.app_debug,
    pool_pre_ping=True,
    pool_size=5,
    connect_args=_sync_connect_args,
)

# Локально (Windows + Docker): отключаем SSL для asyncpg, иначе "connection closed"
_connect_args = {}
if "127.0.0.1" in settings.database_url or "localhost" in settings.database_url:
    _connect_args["ssl"] = False
    _connect_args["timeout"] = 10

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
