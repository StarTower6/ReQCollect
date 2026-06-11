"""Workspace API endpoints.

Routes:
  POST   /api/workspaces          — create workspace
  GET    /api/workspaces           — list workspaces
  GET    /api/workspaces/{id}       — get workspace detail
  PATCH  /api/workspaces/{id}       — update workspace
  DELETE /api/workspaces/{id}       — delete workspace
  GET    /api/workspaces/{id}/sessions  — list sessions in workspace
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from loguru import logger

from app.core.auth import get_current_user
from app.core.file_handler import FileValidationError
from app.core.workspace_analyzer import _fire


def _svc():
    from app.main import get_pm_agent_service
    s = get_pm_agent_service()
    if s is None:
        raise RuntimeError("Service not initialized")
    return s


def _ds():
    from app.main import get_datastore
    d = get_datastore()
    if d is None:
        raise RuntimeError("DataStore not initialized")
    return d


router = APIRouter()


# ── Models ──

from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    code: str = ""
    description: str = ""


class WorkspaceUpdate(BaseModel):
    name: str = ""
    code: str = ""
    description: str = ""


# ── Routes ──


@router.post("/workspaces")
async def ws_create(
    body: WorkspaceCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new workspace."""
    ds = _ds()
    ws = await ds.create_workspace(
        name=body.name,
        created_by=current_user["id"],
        code=body.code,
        description=body.description,
    )
    logger.info(f"Workspace created: {ws['name']} by {current_user['username']}")
    return {"success": True, "workspace": ws}


@router.get("/workspaces")
async def ws_list(
    current_user: dict = Depends(get_current_user),
):
    """List all workspaces accessible by the current user."""
    ds = _ds()
    workspaces = await ds.list_workspaces()
    return {"success": True, "workspaces": workspaces}


@router.get("/workspaces/{workspace_id}")
async def ws_get(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get workspace detail."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"success": True, "workspace": ws}


@router.patch("/workspaces/{workspace_id}")
async def ws_update(
    workspace_id: str,
    body: WorkspaceUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update workspace fields."""
    ds = _ds()
    kwargs = body.model_dump(exclude_unset=True)
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    ws = await ds.update_workspace(workspace_id, **kwargs)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    logger.info(f"Workspace updated: {ws['name']}")
    return {"success": True, "workspace": ws}


@router.delete("/workspaces/{workspace_id}")
async def ws_delete(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a workspace."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await ds.delete_workspace(workspace_id)
    logger.info(f"Workspace deleted: {ws.get('name', workspace_id)}")
    return {"success": True}


@router.get("/workspaces/{workspace_id}/sessions")
async def ws_sessions(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List sessions in a workspace."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    sessions = await ds.list_sessions(workspace_id=workspace_id, limit=10000)
    return {"success": True, "sessions": sessions, "total": len(sessions)}


# ── Workspace File Management ──


@router.get("/workspaces/{workspace_id}/files")
async def ws_files_list(
    workspace_id: str,
    pattern: str = Query(default="*"),
    max_results: int = Query(default=50, le=200),
    current_user: dict = Depends(get_current_user),
):
    """List files in a workspace."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    files = await ds.list_workspace_files(workspace_id, pattern, max_results)
    return {"success": True, "files": files, "total": len(files)}


@router.post("/workspaces/{workspace_id}/files/upload")
async def ws_files_upload(
    workspace_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file to the workspace. Supported: .md .txt .json .yaml .docx .xlsx"""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    content = await file.read()
    filename = file.filename or "untitled"
    try:
        result = await ds.add_workspace_file(workspace_id, filename, content, current_user["id"])
        # Trigger background analysis
        safe_name = result.get("path", "")
        if safe_name:
            _fire(workspace_id, safe_name)
        return {"success": True, "file": result}
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workspaces/{workspace_id}/files/info")
async def ws_files_info(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get workspace file overview: counts by type/source, file list."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    info = await ds.get_workspace_files_info(workspace_id)
    return {"success": True, "info": info}


@router.get("/workspaces/{workspace_id}/files/{path:path}")
async def ws_files_read(
    workspace_id: str,
    path: str,
    max_chars: int = Query(default=8000, le=100000),
    current_user: dict = Depends(get_current_user),
):
    """Read a file from the workspace."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        content = await ds.read_workspace_file(workspace_id, path, max_chars)
        return {"success": True, "file": content}
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/workspaces/{workspace_id}/files/{path:path}")
async def ws_files_delete(
    workspace_id: str,
    path: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a file from the workspace."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    deleted = await ds.remove_workspace_file(workspace_id, path)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    return {"success": True}


# ── Workspace Directory Linking ──


@router.post("/workspaces/{workspace_id}/link")
async def ws_link_dir(
    workspace_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Link a server directory and scan files into the workspace."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    dir_path = body.get("path", "")
    if not dir_path:
        raise HTTPException(400, detail="path is required")
    try:
        result = await ds.link_workspace_directory(workspace_id, dir_path)
        return {"success": True, "result": result}
    except FileNotFoundError as e:
        raise HTTPException(400, detail=str(e))


@router.post("/workspaces/{workspace_id}/unlink")
async def ws_unlink_dir(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Unlink directory and remove all linked files."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    result = await ds.unlink_workspace_directory(workspace_id)
    return {"success": True, "result": result}


@router.post("/workspaces/{workspace_id}/sync")
async def ws_sync_files(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Manually sync linked directory files."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    result = await ds.sync_workspace_files(workspace_id)
    # Trigger analysis on newly added files
    if result.get("added"):
        for fname in result["added"]:
            _fire(workspace_id, fname)
    return {"success": True, "result": result}


@router.get("/workspaces/{workspace_id}/linked-status")
async def ws_linked_status(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get directory link status."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    status = await ds.get_workspace_linked_status(workspace_id)
    return {"success": True, "status": status}
