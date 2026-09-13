"""Async SQLAlchemy engine, session factory, and declarative base."""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from orion.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


async def get_session() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        yield session


@asynccontextmanager
async def get_session_context():
    """Async context manager for database sessions in background tasks.

    Use this when FastAPI's Depends() is unavailable (e.g. BackgroundTask,
    scheduled jobs, CLI scripts).

    Usage::

        async with get_session_context() as session:
            result = await session.execute(stmt)
    """
    async with async_session_factory() as session:
        yield session
