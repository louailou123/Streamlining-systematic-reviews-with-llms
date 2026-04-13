"""
LiRA Backend — Database Initialization
Creates tables and optionally seeds test data.
"""

import asyncio
from app.db.base import Base
from app.db.session import engine

# Import all models to register them with Base.metadata
import app.models  # noqa: F401


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ All database tables created successfully")


async def drop_tables():
    """Drop all database tables. USE WITH CAUTION."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✓ All database tables dropped")


async def init_db():
    """Initialize database: create tables."""
    await create_tables()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
