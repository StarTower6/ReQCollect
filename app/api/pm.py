"""PM Agent API endpoints.

Core endpoints:
  POST /api/pm/chat       Phase 1: requirement mining dialog (SSE)
  POST /api/pm/generate   Phase 2: PRD generation (SSE)
  POST /api/pm/continue   Phase 2: incremental next section (SSE)
  POST /api/pm/agent      Convenience wrapper: auto-routes (SSE)
  POST /api/pm/upload     Upload domain knowledge docs
  GET  /api/pm/profile/{session_id}  View requirement profile
"""

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from app.models.pm import (
    AgentRequest,
    ChatRequest,
    ContinueRequest,
    GenerateRequest,
    SessionPinRequest,
)
from app.services.pm_agent_service import pm_agent_service
from app.services.vector_index_service import vector_index_service

router = APIRouter()


@router.get("/pm/sessions")
async def pm_list_sessions():
    """List all recent sessions."""
    from app.db.database import AsyncSessionLocal
    from app.db.repository import SessionRepository
    async with AsyncSessionLocal() as session:
        sessions = await SessionRepository.list_sessions(session)
    return {"success": True, "sessions": sessions}


@router.get("/pm/history/{session_id}")
async def pm_get_history(session_id: str):
    """Get persisted chat messages for a session."""
    from app.db.database import AsyncSessionLocal
    from app.db.repository import ChatHistoryRepository
    async with AsyncSessionLocal() as session:
        messages = await ChatHistoryRepository.list_by_session(session, session_id)
    return {"success": True, "session_id": session_id, "messages": messages}


@router.patch("/pm/sessions/{session_id}/pin")
async def pm_pin_session(session_id: str, request: SessionPinRequest):
    """Pin or unpin a persisted session."""
    from app.db.database import AsyncSessionLocal
    from app.db.repository import SessionRepository
    async with AsyncSessionLocal() as session:
        updated = await SessionRepository.set_pinned(session, session_id, request.is_pinned)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session": updated}


@router.delete("/pm/sessions/{session_id}")
async def pm_delete_session(session_id: str):
    """Delete a persisted session and its related history."""
    from app.db.database import AsyncSessionLocal
    from app.db.repository import SessionRepository
    async with AsyncSessionLocal() as session:
        deleted = await SessionRepository.delete_session(session, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    await pm_agent_service.forget_session(session_id)
    return {"success": True, "session_id": session_id}


@router.post("/pm/chat")
async def pm_chat(request: ChatRequest):
    """Phase 1: Requirement mining dialog (SSE)."""
    logger.info(f"[{request.session_id}] Chat: {request.message[:100]}...")

    async def gen():
        async for event in pm_agent_service.chat(
            request.message,
            request.session_id,
            use_knowledge=request.use_knowledge,
        ):
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/pm/generate")
async def pm_generate(request: GenerateRequest):
    """Phase 2: Trigger PRD generation (SSE)."""
    logger.info(f"[{request.session_id}] Generate PRD, mode={request.mode}")

    async def gen():
        async for event in pm_agent_service.generate_prd(request.session_id, request.mode):
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/pm/continue")
async def pm_continue(request: ContinueRequest):
    """Phase 2: Continue incremental generation (SSE)."""
    logger.info(f"[{request.session_id}] Continue generation")

    async def gen():
        async for event in pm_agent_service.continue_generation(request.session_id):
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/pm/agent")
async def pm_agent(request: AgentRequest):
    """Convenience wrapper: auto-routes chat/generate/continue (SSE)."""
    logger.info(f"[{request.session_id}] Agent: {request.message[:100]}...")

    async def gen():
        async for event in pm_agent_service.handle(
            request.message,
            request.session_id,
            request.mode,
            use_knowledge=request.use_knowledge,
        ):
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/pm/upload")
async def pm_upload(file: UploadFile = File(...), session_id: str = Form(default="default")):
    """Upload domain knowledge document to Milvus."""
    try:
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / file.filename
        content = await file.read()
        file_path.write_bytes(content)
        vector_index_service.index_single_file(str(file_path.resolve()))
        logger.info(f"[{session_id}] Uploaded: {file.filename}")
        return {"success": True, "filename": file.filename, "message": f"'{file.filename}' indexed."}
    except Exception as e:
        logger.error(f"[{session_id}] Upload failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/pm/profile/{session_id}")
async def pm_get_profile(session_id: str):
    """Get current requirement profile."""
    profile = await pm_agent_service.get_profile(session_id)
    return {"success": True, "session_id": session_id, "profile": profile}
