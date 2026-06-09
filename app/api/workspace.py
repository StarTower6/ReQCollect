"""Workspace API endpoints.

Routes:
  POST   /api/workspaces          — create workspace
  GET    /api/workspaces           — list workspaces
  GET    /api/workspaces/{id}       — get workspace detail
  PATCH  /api/workspaces/{id}       — update workspace
  DELETE /api/workspaces/{id}       — delete workspace
  GET    /api/workspaces/{id}/sessions  — list sessions in workspace
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.core.auth import get_current_user


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
