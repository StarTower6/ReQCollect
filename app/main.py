"""PM Agent FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

import app.core.llm_factory  # noqa: F401 — apply DeepSeek reasoning fix before any LLM imports
from app.api.pm import router as pm_router
from app.config import config
from app.core.milvus_client import milvus_manager
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"Starting {config.app_name} v{config.app_version}...")
    logger.info(f"Environment: {'development' if config.debug else 'production'}")
    logger.info(f"Listening on: http://{config.host}:{config.port}")
    logger.info(f"API docs: http://{config.host}:{config.port}/docs")

    logger.info("Connecting to Milvus...")
    milvus_manager.connect()
    logger.info("Milvus connected")

    logger.info("Initializing MySQL...")
    await init_db()
    logger.info("MySQL initialized")

    logger.info("Initializing VectorStore...")
    from app.services.vector_store_manager import vector_store_manager
    vector_store_manager.initialize()
    logger.info("VectorStore initialized")

    logger.info("=" * 60)
    yield

    logger.info("Shutting down...")
    milvus_manager.close()
    logger.info(f"{config.app_name} stopped")


app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="AI Product Manager Agent — automated requirement mining and PRD generation",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pm_router, prefix="/api", tags=["PM Agent"])

static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": f"Welcome to {config.app_name} API",
        "version": config.app_version,
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
