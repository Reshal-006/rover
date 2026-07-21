from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from apps.backend.app.core.config import settings

is_sqlite = "sqlite" in settings.DATABASE_URL

engine_kwargs = {"echo": False, "future": True}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        from apps.backend.app.domain.models import models
        await conn.run_sync(Base.metadata.create_all)
        
        # Temporary migration to add user_preferences if it doesn't exist
        try:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE users ADD COLUMN user_preferences JSON DEFAULT '{}'"))
        except Exception as e:
            # Column likely already exists
            pass

async def reset_db():
    async with engine.begin() as conn:
        from apps.backend.app.domain.models import models
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
