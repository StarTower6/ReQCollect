"""PM Agent API endpoints (Lite: no database).

Core endpoints:
  POST /api/pm/chat       Phase 1: requirement mining dialog (SSE)
  POST /api/pm/generate   Phase 2: PRD generation (SSE)
  POST /api/pm/continue   Phase 2: incremental next section (SSE)
  POST /api/pm/agent      Convenience wrapper: auto-routes (SSE)
  GET  /api/pm/profile/{session_id}  View requirement profile
  GET  /api/pm/prd/{session_id}      View generated PRD
  GET  /api/pm/sessions   List recent sessions
"""

import json

from fastapi import APIRouter, HTTPException
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from app.models.pm import AgentRequest, ChatRequest, ContinueRequest, GenerateRequest
from app.services.pm_agent_service import pm_agent_service

router = APIRouter()


@router.get("/pm/sessions")
async def pm_list_sessions():
    """List all sessions."""
    sessions = await pm_agent_service.list_sessions()
    return {"success": True, "sessions": sessions}


@router.get("/pm/history/{session_id}")
async def pm_get_history(session_id: str):
    """Get in-memory chat messages for a session."""
    messages = await pm_agent_service.get_message_history(session_id)
    return {"success": True, "session_id": session_id, "messages": messages}


@router.delete("/pm/sessions/{session_id}")
async def pm_delete_session(session_id: str):
    """Delete a session and its data."""
    deleted = await pm_agent_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
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


@router.get("/pm/profile/{session_id}")
async def pm_get_profile(session_id: str):
    """Get current requirement profile."""
    profile = await pm_agent_service.get_profile(session_id)
    return {"success": True, "session_id": session_id, "profile": profile}


@router.get("/pm/prd/{session_id}")
async def pm_get_prd(session_id: str):
    """Get generated PRD for a session."""
    prd = await pm_agent_service.get_prd(session_id)
    if prd is None:
        raise HTTPException(status_code=404, detail="No PRD generated for this session yet")
    return {"success": True, "session_id": session_id, "prd": prd}


@router.get("/pm/version")
async def pm_version():
    """Get PM Agent version info."""
    from app.config import config
    return {
        "app_name": config.app_name,
        "version": config.app_version,
        "llm_model": config.llm_model,
        "llm_base_url": config.llm_base_url,
    }
