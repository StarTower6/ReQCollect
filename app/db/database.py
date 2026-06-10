"""Async SQLAlchemy engine and session management for MySQL (asyncmy)."""

from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import config
from app.db.models import Base


_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None
_initialized = False


def _get_mysql_dsn() -> str:
    """Build async DSN from config."""
    return (
        f"mysql+asyncmy://{config.mysql_user}:{config.mysql_password}"
        f"@{config.mysql_host}:{config.mysql_port}/{config.mysql_database}"
        f"?charset=utf8mb4"
    )


async def init_db() -> bool:
    """Initialize the MySQL engine, create tables, and return True on success.

    Returns False if MySQL is unavailable (caller decides fallback).
    """
    global _engine, _async_session_factory, _initialized

    if _initialized:
        return True

    if not config.mysql_host:
        logger.info("MySQL not configured, will use JSON file fallback")
        return False

    dsn = _get_mysql_dsn()
    try:
        _engine = create_async_engine(
            dsn,
            pool_size=config.mysql_pool_size,
            max_overflow=config.mysql_max_overflow,
            echo=config.debug,
            pool_pre_ping=True,
        )
        # Test connection
        async with _engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        # Create all tables
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Apply idempotent migrations
        async with _engine.begin() as conn:
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "ALTER TABLE sessions ADD COLUMN workspace_id VARCHAR(64) DEFAULT '' AFTER id"
                    )
                )
                logger.info("Applied migration: sessions.workspace_id")
            except Exception:
                logger.debug("Migration: sessions.workspace_id already exists")

        # wiki_pages table
        async with _engine.begin() as conn:
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "CREATE TABLE IF NOT EXISTS wiki_pages ("
                        "id VARCHAR(64) PRIMARY KEY, "
                        "workspace_id VARCHAR(64) NOT NULL, "
                        "title VARCHAR(255) NOT NULL, "
                        "content TEXT, "
                        "created_by VARCHAR(64) NOT NULL, "
                        "updated_by VARCHAR(64) DEFAULT '', "
                        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                        "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
                        "INDEX idx_wiki_workspace (workspace_id)"
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
                    )
                )
                logger.info("Applied migration: wiki_pages table")
            except Exception:
                logger.debug("Migration: wiki_pages table already exists")

        # wiki_links table
        async with _engine.begin() as conn:
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "CREATE TABLE IF NOT EXISTS wiki_links ("
                        "id VARCHAR(64) PRIMARY KEY, "
                        "source_page_id VARCHAR(64) NOT NULL, "
                        "target_page_id VARCHAR(64) NOT NULL, "
                        "link_type VARCHAR(50) DEFAULT 'reference', "
                        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                        "INDEX idx_wikilink_source (source_page_id), "
                        "INDEX idx_wikilink_target (target_page_id)"
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
                    )
                )
                logger.info("Applied migration: wiki_links table")
            except Exception:
                logger.debug("Migration: wiki_links table already exists")

        _async_session_factory = async_sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
        _initialized = True
        logger.info("MySQL connected and tables synced")
        return True
    except Exception as e:
        logger.warning(f"MySQL unavailable ({e}), falling back to JSON file storage")
        await close_db()
        return False


async def close_db():
    """Dispose the engine."""
    global _engine, _async_session_factory, _initialized

    _initialized = False
    _async_session_factory = None
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("MySQL engine disposed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session (FastAPI dependency)."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with _async_session_factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Return the session factory for direct use."""
    return _async_session_factory
