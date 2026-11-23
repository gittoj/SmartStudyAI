from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# pre_ping replaces connections the database dropped while idle (Neon suspends its compute when quiet).
engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
