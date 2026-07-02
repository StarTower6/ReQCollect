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

        # wiki_links table — with idempotent migration from old schema
        async with _engine.begin() as conn:
            # Check if old table exists and migrate columns
            try:
                result = await conn.execute(
                    __import__("sqlalchemy").text(
                        "SHOW COLUMNS FROM wiki_links LIKE 'source_page_id'"
                    )
                )
                if result.fetchone():
                    # Old schema: rename columns
                    await conn.execute(__import__("sqlalchemy").text(
                        "ALTER TABLE wiki_links CHANGE source_page_id source_ref VARCHAR(128) NOT NULL"
                    ))
                    await conn.execute(__import__("sqlalchemy").text(
                        "ALTER TABLE wiki_links CHANGE target_page_id target_ref VARCHAR(128) NOT NULL"
                    ))
                    await conn.execute(__import__("sqlalchemy").text(
                        "ALTER TABLE wiki_links ADD COLUMN source_type VARCHAR(16) DEFAULT 'wiki' AFTER source_ref"
                    ))
                    await conn.execute(__import__("sqlalchemy").text(
                        "ALTER TABLE wiki_links ADD COLUMN target_type VARCHAR(16) DEFAULT 'wiki' AFTER target_ref"
                    ))
                    await conn.execute(__import__("sqlalchemy").text(
                        "ALTER TABLE wiki_links ADD COLUMN workspace_id VARCHAR(64) DEFAULT '' AFTER link_type"
                    ))
                    await conn.execute(__import__("sqlalchemy").text(
                        "ALTER TABLE wiki_links ADD INDEX idx_wikilink_source (source_ref)"
                    ))
                    await conn.execute(__import__("sqlalchemy").text(
                        "ALTER TABLE wiki_links ADD INDEX idx_wikilink_target (target_ref)"
                    ))
                    await conn.execute(__import__("sqlalchemy").text(
                        "ALTER TABLE wiki_links ADD INDEX idx_wikilink_workspace (workspace_id)"
                    ))
                    logger.info("Applied migration: wiki_links schema upgrade (source_page_id -> source_ref)")
            except Exception as e:
                logger.debug(f"Migration: wiki_links upgrade skipped ({e})")

            # Ensure new schema table exists for fresh installs
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "CREATE TABLE IF NOT EXISTS wiki_links ("
                        "id VARCHAR(64) PRIMARY KEY, "
                        "source_ref VARCHAR(128) NOT NULL, "
                        "source_type VARCHAR(16) DEFAULT 'wiki', "
                        "target_ref VARCHAR(128) NOT NULL, "
                        "target_type VARCHAR(16) DEFAULT 'wiki', "
                        "link_type VARCHAR(50) DEFAULT 'reference', "
                        "workspace_id VARCHAR(64) DEFAULT '', "
                        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                        "INDEX idx_wikilink_source (source_ref), "
                        "INDEX idx_wikilink_target (target_ref), "
                        "INDEX idx_wikilink_workspace (workspace_id)"
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
                    )
                )
                logger.info("Applied migration: wiki_links table")
            except Exception:
                logger.debug("Migration: wiki_links table already exists")

            # Migration: requirement_proposals table
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "CREATE TABLE IF NOT EXISTS requirement_proposals ("
                        "id VARCHAR(64) PRIMARY KEY, "
                        "workspace_id VARCHAR(64) NOT NULL DEFAULT '', "
                        "source_session_id VARCHAR(64) DEFAULT '', "
                        "submitter_id VARCHAR(64) DEFAULT '', "
                        "title VARCHAR(500) DEFAULT '', "
                        "background TEXT, "
                        "pain_points JSON, "
                        "desired_outcome TEXT, "
                        "scope_note TEXT, "
                        "urgency VARCHAR(10) DEFAULT 'medium', "
                        "priority VARCHAR(10) DEFAULT 'P2', "
                        "ai_assessment TEXT, "
                        "status VARCHAR(20) DEFAULT 'pending_review', "
                        "tags JSON, "
                        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                        "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
                        "INDEX idx_rp_workspace (workspace_id), "
                        "INDEX idx_rp_status (status), "
                        "INDEX idx_rp_submitter (submitter_id)"
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
                    )
                )
                logger.info("Applied migration: requirement_proposals table")
            except Exception:
                logger.debug("Migration: requirement_proposals table already exists")

            # Migration: generated_prds.source_proposal_ids
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "ALTER TABLE generated_prds ADD COLUMN source_proposal_ids JSON DEFAULT NULL AFTER mode"
                    )
                )
                logger.info("Applied migration: generated_prds.source_proposal_ids")
            except Exception:
                logger.debug("Migration: generated_prds.source_proposal_ids already exists")

            # Migration: generated_prds.workspace_id
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "ALTER TABLE generated_prds ADD COLUMN workspace_id VARCHAR(64) DEFAULT '' AFTER session_id"
                    )
                )
                logger.info("Applied migration: generated_prds.workspace_id")
            except Exception:
                logger.debug("Migration: generated_prds.workspace_id already exists")

            # Migration: workspace_members table
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "CREATE TABLE IF NOT EXISTS workspace_members ("
                        "id VARCHAR(64) PRIMARY KEY, "
                        "workspace_id VARCHAR(64) NOT NULL, "
                        "user_id VARCHAR(64) NOT NULL, "
                        "role_in_workspace VARCHAR(20) DEFAULT 'business', "
                        "joined_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                        "INDEX idx_wm_workspace (workspace_id), "
                        "INDEX idx_wm_user (user_id), "
                        "UNIQUE KEY uq_ws_user (workspace_id, user_id), "
                        "CONSTRAINT fk_wm_workspace FOREIGN KEY (workspace_id) "
                        "REFERENCES workspaces(id) ON DELETE CASCADE, "
                        "CONSTRAINT fk_wm_user FOREIGN KEY (user_id) "
                        "REFERENCES users(id) ON DELETE CASCADE"
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
                    )
                )
                logger.info("Applied migration: workspace_members table")
            except Exception as e:
                logger.debug(f"Migration: workspace_members table skipped ({e})")

            # Migration: backfill existing workspaces' created_by as owner members
            try:
                ws_rows = await conn.execute(
                    __import__("sqlalchemy").text(
                        "SELECT id, created_by FROM workspaces"
                    )
                )
                for ws_id, created_by in ws_rows.fetchall():
                    if not created_by:
                        continue
                    # Skip if user doesn't exist (FK constraint would fail)
                    user_exists = await conn.execute(
                        __import__("sqlalchemy").text(
                            "SELECT 1 FROM users WHERE id = :u"
                        ),
                        {"u": created_by},
                    )
                    if not user_exists.fetchone():
                        continue
                    existing = await conn.execute(
                        __import__("sqlalchemy").text(
                            "SELECT 1 FROM workspace_members "
                            "WHERE workspace_id = :ws AND user_id = :u"
                        ),
                        {"ws": ws_id, "u": created_by},
                    )
                    if existing.fetchone():
                        continue
                    import uuid as _uuid
                    await conn.execute(
                        __import__("sqlalchemy").text(
                            "INSERT INTO workspace_members (id, workspace_id, user_id, role_in_workspace) "
                            "VALUES (:id, :ws, :u, 'owner')"
                        ),
                        {"id": _uuid.uuid4().hex[:16], "ws": ws_id, "u": created_by},
                    )
                logger.info("Applied migration: backfill workspace owners as members")
            except Exception as e:
                logger.debug(f"Migration: backfill workspace members skipped ({e})")

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
