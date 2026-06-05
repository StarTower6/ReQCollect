"""PM Agent API endpoints.

Storage-backed endpoints (MySQL or JSON file fallback):
  POST /api/pm/chat        Phase 1: requirement mining dialog (SSE)
  POST /api/pm/generate    Phase 2: PRD generation (SSE)
  POST /api/pm/continue    Phase 2: incremental next section (SSE)
  POST /api/pm/agent       Convenience wrapper: auto-routes (SSE)
  GET  /api/pm/sessions    List sessions (persistent)
  GET  /api/pm/history/{session_id}  Chat messages
  DELETE /api/pm/sessions/{session_id}   Delete session
  GET  /api/pm/profile/{session_id}  View requirement profile
  GET  /api/pm/prd/{session_id}  View generated PRD
  GET  /api/pm/version     App info

  P1 — Data services:
  GET  /api/pm/dashboard/overview
  GET  /api/pm/dashboard/trend
  GET  /api/pm/export/sessions  (CSV or XLSX)
  GET  /api/pm/export/prds      (XLSX)
"""

import csv
import io
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from app.models.pm import AgentRequest, ChatRequest, ContinueRequest, GenerateRequest
from app.services.pm_agent_service import pm_agent_service

router = APIRouter()


# ── Session management ──


@router.get("/pm/sessions")
async def pm_list_sessions(
    user_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List sessions with optional filters, ordered by updated_at desc."""
    sessions = await pm_agent_service.list_sessions()
    # Filtering (DataStore supports server-side, but we do client-side for file fallback compat)
    if user_id:
        sessions = [s for s in sessions if s.get("user_id") == user_id]
    if status:
        sessions = [s for s in sessions if s.get("status") == status]
    return {"success": True, "sessions": sessions[offset : offset + limit], "total": len(sessions)}


@router.get("/pm/history/{session_id}")
async def pm_get_history(
    session_id: str,
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Get chat messages for a session (persistent)."""
    messages = await pm_agent_service.get_message_history(session_id)
    return {
        "success": True,
        "session_id": session_id,
        "messages": messages[offset : offset + limit],
        "total": len(messages),
    }


@router.delete("/pm/sessions/{session_id}")
async def pm_delete_session(session_id: str):
    """Delete a session and all related data."""
    deleted = await pm_agent_service.delete_session(session_id)
    await pm_agent_service.log_audit("delete", session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id}


# ── Phase 1: Chat ──


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


# ── Phase 2: PRD Generation ──


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


# ── Convenience wrapper ──


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


# ── Profile / PRD access ──


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


# ── Dashboard (P1) ──


@router.get("/pm/dashboard/overview")
async def pm_dashboard_overview():
    """Get aggregated dashboard overview: sessions by status, avg sufficiency, totals."""
    overview = await pm_agent_service.get_dashboard_overview()
    return {"success": True, "data": overview}


@router.get("/pm/dashboard/trend")
async def pm_dashboard_trend(
    granularity: str = Query(default="day", pattern="^(day|week|month)$"),
    days: int = Query(default=30, ge=1, le=365),
):
    """Get time-series trend data of session and PRD creation counts."""
    trend = await pm_agent_service.get_trend_data(granularity, days)
    return {"success": True, "data": trend}


# ── Export (P1) ──


@router.get("/pm/export/sessions")
async def pm_export_sessions(
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
):
    """Export session list as CSV or XLSX."""
    sessions = await pm_agent_service.export_sessions()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["session_id", "user_id", "project_name", "status",
                         "sufficiency_score", "created_at", "updated_at"])
        for s in sessions:
            writer.writerow([
                s.get("session_id", ""),
                s.get("user_id", ""),
                s.get("project_name", ""),
                s.get("status", ""),
                s.get("sufficiency_score", 0),
                s.get("created_at", ""),
                s.get("updated_at", ""),
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sessions.csv"},
        )

    # XLSX export
    return await _export_xlsx(
        filename="sessions.xlsx",
        headers=["session_id", "user_id", "project_name", "status",
                 "sufficiency_score", "created_at", "updated_at"],
        rows=[[
            s.get("session_id", ""),
            s.get("user_id", ""),
            s.get("project_name", ""),
            s.get("status", ""),
            s.get("sufficiency_score", 0),
            s.get("created_at", ""),
            s.get("updated_at", ""),
        ] for s in sessions],
    )


@router.get("/pm/export/prds")
async def pm_export_prds(
    format: str = Query(default="xlsx", pattern="^(csv|xlsx)$"),
):
    """Export generated PRDs as XLSX or CSV."""
    prds = await pm_agent_service.export_prds()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["session_id", "project_name", "version", "mode",
                         "created_at", "markdown_preview"])
        for p in prds:
            writer.writerow([
                p.get("session_id", ""),
                p.get("project_name", ""),
                p.get("version", 1),
                p.get("mode", ""),
                p.get("created_at", ""),
                p.get("markdown_preview", ""),
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=prds.csv"},
        )

    return await _export_xlsx(
        filename="prds.xlsx",
        headers=["session_id", "project_name", "version", "mode",
                 "created_at", "markdown_preview"],
        rows=[[
            p.get("session_id", ""),
            p.get("project_name", ""),
            p.get("version", 1),
            p.get("mode", ""),
            p.get("created_at", ""),
            p.get("markdown_preview", ""),
        ] for p in prds],
    )


async def _export_xlsx(
    filename: str,
    headers: list[str],
    rows: list[list],
) -> StreamingResponse:
    """Helper to generate XLSX via openpyxl and return StreamingResponse."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Export"

    # Header row
    header_font = Font(bold=True)
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font

    # Data rows
    for row_idx, row_data in enumerate(rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-adjust column widths
    for col_idx, h in enumerate(headers, 1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = max(
            len(str(h)) + 2,
            max((len(str(row[col_idx - 1])) if col_idx <= len(row) else 0)
                for row in rows) + 2 if rows else 10,
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Version ──


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
