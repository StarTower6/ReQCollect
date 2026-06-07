"""PM Agent FastAPI application entry point.

Bootstrap sequence:
  1. Validate critical config
  2. Try MySQL (asyncmy + SQLAlchemy)
  3. Fall back to JSON file storage if MySQL unavailable
  4. Wire DataStore into the service layer

Graceful shutdown: SIGTERM handled by uvicorn/gunicorn automatically.
"""

import os
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api.auth import router as auth_router
from app.api.pm import router as pm_router
from app.config import config


_datastore = None
_pm_agent_service = None

# ── Graceful shutdown flag ──
_shutting_down = False


def get_datastore():
    """Return the initialized DataStore instance."""
    return _datastore


def get_pm_agent_service():
    """Return the initialized PMAgentService instance."""
    return _pm_agent_service


def _validate_config():
    """Warn about missing but non-critical config at startup.

    Returns True if config is minimally viable.
    """
    issues = []

    if not config.llm_api_key:
        issues.append("LLM_API_KEY not set — LLM calls will fail")
    if not config.llm_base_url:
        issues.append("LLM_BASE_URL not set — using default")

    if config.mysql_required and not config.mysql_host:
        issues.append("MYSQL_HOST not set but mysql_required=True — will fail")

    for issue in issues:
        logger.warning(f"Config issue: {issue}")

    # LLM API key is critical — warn but don't block (dev can start without LLM)
    if not config.llm_api_key:
        logger.warning("LLM not configured. Chat/PRD endpoints will fail until LLM_API_KEY is set.")


def _handle_sigterm(signum, frame):
    """Handle SIGTERM for graceful shutdown (Docker stop)."""
    global _shutting_down
    _shutting_down = True
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"Starting {config.app_name} v{config.app_version}...")
    logger.info(f"Environment: {'development' if config.debug else 'production'}")
    logger.info(f"Listening on: http://{config.host}:{config.port}")
    logger.info(f"API docs: http://{config.host}:{config.port}/docs")

    os.makedirs(config.data_dir, exist_ok=True)
    logger.info(f"Data directory: {config.data_dir}")

    # Step 0: Validate config
    _validate_config()

    # Step 1: Try MySQL, fall back to JSON files
    from app.db import create_datastore
    from app.db.database import init_db as init_mysql

    use_mysql = await init_mysql()
    if not use_mysql and config.mysql_required:
        logger.error("MySQL required by config but unavailable — shutting down.")
        raise RuntimeError("MySQL connection failed and mysql_required=True")

    global _datastore, _pm_agent_service
    _datastore = create_datastore(use_mysql)
    logger.info(f"Using storage backend: {'MySQL' if use_mysql else 'JSON file'}")

    # Step 2: Create service with DataStore
    from app.services.pm_agent_service import PMAgentService as _PAS

    _pm_agent_service = _PAS(_datastore)

    # Wire into API module (swap the sentinel)
    import app.services.pm_agent_service as _svc_mod
    _svc_mod.pm_agent_service = _pm_agent_service

    # Step 2a: Ensure default admin user exists
    from app.core.auth import hash_password as _hash_pwd
    try:
        existing = await _datastore.get_user_by_username("admin")
        if existing is None:
            await _datastore.create_user(
                username="admin",
                password_hash=_hash_pwd("admin123"),
                display_name="管理员",
                role="admin",
            )
            logger.info("Default admin user created (admin / admin123)")
    except Exception as _exc:
        logger.warning(f"Could not create default admin user: {_exc}")

    # Step 3: Register SIGTERM handler for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_sigterm)

    logger.info("=" * 60)
    yield

    logger.info(f"{config.app_name} stopped")
    from app.db.database import close_db as close_mysql
    await close_mysql()

    if _pm_agent_service is not None:
        await _pm_agent_service.cleanup()


app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="ReQCollect — conversational business requirement elicitation and analysis system",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api", tags=["Auth"])
app.include_router(pm_router, prefix="/api", tags=["PM Agent"])

static_dir = "static"
_vue_dist = "reqcollect-web/dist"

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount Vue SPA assets for production
if os.path.exists(_vue_dist):
    assets_dir = os.path.join(_vue_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="vue-assets")


@app.get("/")
async def root():
    # Prefer Vue SPA, fall back to legacy static index.html
    for dir in [_vue_dist, static_dir]:
        idx = os.path.join(dir, "index.html")
        if os.path.exists(idx):
            return FileResponse(idx)
    return {
        "message": f"Welcome to {config.app_name} API",
        "version": config.app_version,
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    backend_status = "ok"
    backend_type = "unknown"
    if _datastore is not None:
        try:
            h = await _datastore.health()
            backend_type = h.get("backend", "unknown")
        except Exception:
            backend_status = "degraded"
    return {
        "status": backend_status,
        "backend": backend_type,
        "shutting_down": _shutting_down,
    }
