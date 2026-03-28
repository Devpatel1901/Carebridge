from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import get_settings

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            yield session


async def init_db() -> None:
    """Enable WAL mode for SQLite and create tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("PRAGMA journal_mode=WAL")
        )


async def create_all_tables() -> None:
    from shared.db.models import Base
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
