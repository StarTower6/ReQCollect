"""Async SQLAlchemy engine and session management."""

import asyncio
import random

from loguru import logger
from pymysql.err import OperationalError as PyMySQLOperationalError
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import config

_engine = None
AsyncSessionLocal = None


def _ensure_engine():
    global _engine, AsyncSessionLocal
    if _engine is None:
        _engine = create_async_engine(
            config.database_url,
            echo=config.debug,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
        )
        AsyncSessionLocal = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )


async def init_db():
    """Create all tables. Call on app startup. Retries on concurrent DDL."""
    from app.db.models import Base
    _ensure_engine()

    # Jitter to reduce concurrent DDL collisions with multi-replica deploys
    await asyncio.sleep(random.uniform(0, 1.0))

    for attempt in range(5):
        try:
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.run_sync(_ensure_requirement_profile_schema)
            logger.info("MySQL tables created/verified")
            return
        except PyMySQLOperationalError as e:
            code = getattr(e, 'args', [])[0] if e.args else 0
            if code == 1684:
                logger.warning(f"DDL conflict (attempt {attempt+1}/5), retrying...")
                await asyncio.sleep(1.0 * (attempt + 1))
            else:
                raise


async def get_session() -> AsyncSession:
    _ensure_engine()
    async with AsyncSessionLocal() as session:
        yield session


def _ensure_requirement_profile_schema(sync_conn) -> None:
    """Add columns that create_all cannot add to existing deployments."""
    inspector = inspect(sync_conn)
    table_names = inspector.get_table_names()
    if "requirement_profiles" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("requirement_profiles")}
    if "is_pinned" not in columns:
        sync_conn.exec_driver_sql(
            "ALTER TABLE requirement_profiles ADD COLUMN is_pinned BOOLEAN NOT NULL DEFAULT 0"
        )
        logger.info("Added requirement_profiles.is_pinned column")
