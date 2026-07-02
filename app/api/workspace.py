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

from app.core.auth import get_current_user, require_role, require_reviewer
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


async def _require_workspace_member(workspace_id: str, current_user: dict) -> None:
    """Raise 403 if the user is not a member of the workspace (admin always ok)."""
    if current_user.get("role") == "admin":
        return
    ds = _ds()
    if not await ds.is_workspace_member(workspace_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="无权访问此工作空间")


async def _require_workspace_owner_or_admin(workspace_id: str, current_user: dict) -> None:
    """Raise 403 unless the user is the workspace owner or admin."""
    if current_user.get("role") == "admin":
        return
    ds = _ds()
    role = await ds.get_workspace_member_role(workspace_id, current_user["id"])
    if role != "owner":
        raise HTTPException(status_code=403, detail="仅工作空间所有者或管理员可执行此操作")


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
    current_user: dict = Depends(require_role("analyst", "admin")),
):
    """Create a new workspace. Only analyst/admin can create."""
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
    """List workspaces accessible by the current user (membership-filtered)."""
    ds = _ds()
    # admin sees all; others see only workspaces they're a member of
    uid = None if current_user.get("role") == "admin" else current_user["id"]
    workspaces = await ds.list_workspaces(user_id=uid)
    return {"success": True, "workspaces": workspaces}


@router.get("/workspaces/{workspace_id}")
async def ws_get(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get workspace detail (members only)."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_member(workspace_id, current_user)
    return {"success": True, "workspace": ws}


@router.patch("/workspaces/{workspace_id}")
async def ws_update(
    workspace_id: str,
    body: WorkspaceUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update workspace fields (owner/admin only)."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_owner_or_admin(workspace_id, current_user)
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
    """Delete a workspace (owner/admin only)."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_owner_or_admin(workspace_id, current_user)
    await ds.delete_workspace(workspace_id)
    logger.info(f"Workspace deleted: {ws.get('name', workspace_id)}")
    return {"success": True}


# ── Workspace PRDs ──


@router.get("/workspaces/{workspace_id}/prds")
async def ws_prds_list(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all PRDs in a workspace."""
    ds = _ds()
    ws_obj = await ds.get_workspace(workspace_id)
    if ws_obj is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    prds = await ds.list_prds_by_workspace(workspace_id)
    return {"success": True, "prds": prds, "total": len(prds)}


@router.get("/workspaces/{workspace_id}/sessions")
async def ws_sessions(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List sessions in a workspace (members only)."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_member(workspace_id, current_user)

    sessions = await ds.list_sessions(workspace_id=workspace_id, limit=10000)
    # business only sees their own sessions within the workspace
    if current_user.get("role") == "business":
        sessions = [s for s in sessions if s.get("user_id") == current_user["id"]]
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


@router.get("/workspaces/{workspace_id}/files/related")
async def ws_files_related(
    workspace_id: str,
    path: str = Query(default=""),
    threshold: float = Query(default=0.3, ge=0, le=1),
    current_user: dict = Depends(get_current_user),
):
    """Find files related by tag similarity using Jaccard overlap."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    if not path:
        return {"success": True, "related": []}
    from app.core.workspace_files import WorkspaceFileManager
    fm = WorkspaceFileManager(workspace_id)
    related = fm.get_related_files(path, threshold)
    return {"success": True, "related": related}


# ── Folder Management ──


@router.get("/workspaces/{workspace_id}/folders")
async def ws_folders_list(
    workspace_id: str,
    tree: bool = Query(default=False),
    current_user: dict = Depends(get_current_user),
):
    """List folders. Use tree=true to get nested structure."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    from app.core.workspace_files import WorkspaceFileManager
    fm = WorkspaceFileManager(workspace_id)
    if tree:
        return {"success": True, "folders": fm.get_folder_tree()}
    return {"success": True, "folders": fm.list_folders()}


class FolderCreate(BaseModel):
    name: str
    parent_id: str = ""


@router.post("/workspaces/{workspace_id}/folders")
async def ws_folders_create(
    workspace_id: str,
    body: FolderCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new folder."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    from app.core.workspace_files import WorkspaceFileManager
    fm = WorkspaceFileManager(workspace_id)
    try:
        folder = fm.create_folder(body.name, body.parent_id)
        return {"success": True, "folder": folder}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


class FolderRename(BaseModel):
    name: str


@router.patch("/workspaces/{workspace_id}/folders/{folder_id}")
async def ws_folders_update(
    workspace_id: str,
    folder_id: str,
    body: FolderRename,
    current_user: dict = Depends(get_current_user),
):
    """Rename a folder."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    from app.core.workspace_files import WorkspaceFileManager
    fm = WorkspaceFileManager(workspace_id)
    try:
        folder = fm.rename_folder(folder_id, body.name)
        if folder is None:
            raise HTTPException(404, detail="Folder not found")
        return {"success": True, "folder": folder}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.delete("/workspaces/{workspace_id}/folders/{folder_id}")
async def ws_folders_delete(
    workspace_id: str,
    folder_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a folder. Files in it are unlinked, sub-folders become root-level."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    from app.core.workspace_files import WorkspaceFileManager
    fm = WorkspaceFileManager(workspace_id)
    ok = fm.delete_folder(folder_id)
    if not ok:
        raise HTTPException(404, detail="Folder not found")
    return {"success": True}


class FileFolderAssign(BaseModel):
    folder_id: str  # "" to unlink from folder


@router.patch("/workspaces/{workspace_id}/files/{path:path}/folder")
async def ws_file_set_folder(
    workspace_id: str,
    path: str,
    body: FileFolderAssign,
    current_user: dict = Depends(get_current_user),
):
    """Assign a file to a folder. folder_id="" to unlink."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(404, detail="Workspace not found")
    from app.core.workspace_files import WorkspaceFileManager
    fm = WorkspaceFileManager(workspace_id)
    fm.set_file_folder(path, body.folder_id)
    return {"success": True}


# ── Requirement Proposals ──


class ProposalCreate(BaseModel):
    title: str = ""
    background: str = ""
    pain_points: list = []
    desired_outcome: str = ""
    scope_note: str = ""
    urgency: str = "medium"
    tags: list = []
    source_session_id: str = ""
    submitter_id: str = ""


class ProposalUpdate(BaseModel):
    title: str = ""
    background: str = ""
    pain_points: list | None = None
    desired_outcome: str = ""
    scope_note: str = ""
    urgency: str = ""
    priority: str = ""
    status: str = ""
    ai_assessment: str = ""
    tags: list | None = None


@router.post("/workspaces/{workspace_id}/proposals")
async def ws_proposal_create(
    workspace_id: str,
    body: ProposalCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a requirement proposal in a workspace."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    proposal = await ds.create_proposal(
        workspace_id=workspace_id,
        title=body.title,
        background=body.background,
        pain_points=body.pain_points,
        desired_outcome=body.desired_outcome,
        scope_note=body.scope_note,
        urgency=body.urgency,
        tags=body.tags,
        source_session_id=body.source_session_id,
        submitter_id=body.submitter_id or current_user.get("id", ""),
    )
    logger.info(f"Proposal created: {proposal['id']} in workspace {workspace_id}")
    return {"success": True, "proposal": proposal}


@router.get("/workspaces/{workspace_id}/proposals")
async def ws_proposal_list(
    workspace_id: str,
    status: str | None = Query(default=None),
    urgency: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List proposals in a workspace with optional filters (members only).

    business role only sees proposals they submitted.
    """
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_member(workspace_id, current_user)
    proposals = await ds.list_proposals(
        workspace_id=workspace_id,
        status=status,
        urgency=urgency,
        priority=priority,
        limit=limit,
        offset=offset,
    )
    if current_user.get("role") == "business":
        proposals = [p for p in proposals if p.get("submitter_id") == current_user["id"]]
    return {"success": True, "proposals": proposals, "total": len(proposals)}


@router.get("/workspaces/{workspace_id}/proposals/{proposal_id}")
async def ws_proposal_get(
    workspace_id: str,
    proposal_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a proposal detail."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    proposal = await ds.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return {"success": True, "proposal": proposal}


@router.patch("/workspaces/{workspace_id}/proposals/{proposal_id}")
async def ws_proposal_update(
    workspace_id: str,
    proposal_id: str,
    body: ProposalUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update proposal fields.

    Content fields (title, background, pain_points, etc.) require analyst/admin.
    The *status* field requires reviewer/analyst/admin.
    business can only view, not edit.
    """
    role = current_user.get("role")
    kwargs = body.model_dump(exclude_unset=True)

    # Status change requires reviewer/analyst/admin
    if kwargs.get("status"):
        if role not in ("reviewer", "analyst", "admin"):
            raise HTTPException(
                status_code=403,
                detail="修改提案状态需要 reviewer/analyst/admin 权限",
            )

    # Content fields (anything other than status) require analyst/admin
    content_keys = {k: v for k, v in kwargs.items() if k != "status"}
    if content_keys:
        if role not in ("analyst", "admin"):
            raise HTTPException(
                status_code=403,
                detail="编辑提案内容需要 analyst/admin 权限",
            )

    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_member(workspace_id, current_user)
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    proposal = await ds.update_proposal(proposal_id, **kwargs)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    logger.info(f"Proposal updated: {proposal['id']}")
    return {"success": True, "proposal": proposal}


@router.delete("/workspaces/{workspace_id}/proposals/{proposal_id}")
async def ws_proposal_delete(
    workspace_id: str,
    proposal_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a proposal."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    deleted = await ds.delete_proposal(proposal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proposal not found")
    logger.info(f"Proposal deleted: {proposal_id}")
    return {"success": True}


# ── Proposal Review ──


class ProposalReviewBody(BaseModel):
    action: str  # "approve" | "reject" | "reopen"
    comment: str = ""


@router.post("/workspaces/{workspace_id}/proposals/{proposal_id}/review")
async def ws_proposal_review(
    workspace_id: str,
    proposal_id: str,
    body: ProposalReviewBody,
    current_user: dict = Depends(require_reviewer),
):
    """Review a proposal: approve, reject, or reopen.

    Status transitions:
      approve  -> approved
      reject   -> rejected
      reopen   -> pending_review
    """
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "reopen": "pending_review",
    }
    new_status = status_map.get(body.action)
    if not new_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid review action: {body.action}. Use approve/reject/reopen",
        )

    existing = await ds.get_proposal(proposal_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    updated = await ds.update_proposal(proposal_id, status=new_status)
    if updated is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Append reviewer note to ai_assessment
    reviewer_note = ""
    if body.comment:
        reviewer_name = current_user.get("username", current_user.get("id", "unknown"))
        reviewer_note = f"\n[Review by {reviewer_name}] {body.comment}"

    if reviewer_note:
        existing_ai = existing.get("ai_assessment", "") or ""
        new_ai = existing_ai + reviewer_note
        await ds.update_proposal(proposal_id, ai_assessment=new_ai)
        updated["ai_assessment"] = new_ai

    logger.info(
        f"Proposal {proposal_id} reviewed: {new_status} "
        f"by {current_user.get('username', '?')}"
    )
    return {"success": True, "proposal": updated}


# ── Workspace Members ──


class AddMemberBody(BaseModel):
    user_id: str
    role: str = "business"  # owner/analyst/reviewer/business


@router.post("/workspaces/{workspace_id}/members")
async def ws_add_member(
    workspace_id: str,
    body: AddMemberBody,
    current_user: dict = Depends(get_current_user),
):
    """Add a member to the workspace (owner/admin only)."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_owner_or_admin(workspace_id, current_user)
    # Validate user exists
    target = await ds.get_user_by_id(body.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.role not in ("owner", "analyst", "reviewer", "business"):
        raise HTTPException(status_code=400, detail="无效的角色")
    member = await ds.add_workspace_member(workspace_id, body.user_id, body.role)
    logger.info(
        f"Member added: {body.user_id} -> {workspace_id} ({body.role}) "
        f"by {current_user.get('username', '?')}"
    )
    return {"success": True, "member": member}


@router.delete("/workspaces/{workspace_id}/members/{user_id}")
async def ws_remove_member(
    workspace_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove a member from the workspace (owner/admin only)."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_owner_or_admin(workspace_id, current_user)
    # Don't allow removing the last owner
    members = await ds.list_workspace_members(workspace_id)
    owners = [m for m in members if m.get("role_in_workspace") == "owner"]
    if user_id in [m.get("user_id") for m in owners] and len(owners) <= 1:
        raise HTTPException(status_code=400, detail="不能移除最后一个所有者")
    removed = await ds.remove_workspace_member(workspace_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="成员不存在")
    logger.info(
        f"Member removed: {user_id} <- {workspace_id} "
        f"by {current_user.get('username', '?')}"
    )
    return {"success": True}


@router.get("/workspaces/{workspace_id}/members")
async def ws_list_members(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List members of a workspace (members only)."""
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_member(workspace_id, current_user)
    members = await ds.list_workspace_members(workspace_id)
    return {"success": True, "members": members, "total": len(members)}


# ── Proposal Refine ──


@router.post("/workspaces/{workspace_id}/proposals/{proposal_id}/refine")
async def ws_proposal_refine(
    workspace_id: str,
    proposal_id: str,
    current_user: dict = Depends(require_role("analyst", "admin")),
):
    """Create a chat session seeded with the proposal's context for AI-assisted refining.

    Returns the new session_id. The session's first system message carries
    meta.refine_proposal_id so ChatView can detect it and offer "apply to proposal".
    """
    import uuid

    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await _require_workspace_member(workspace_id, current_user)
    proposal = await ds.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    session_id = f"refine-{uuid.uuid4().hex[:12]}"
    await ds.create_session(
        session_id,
        user_id=current_user["id"],
        project_name=f"完善提案: {proposal.get('title') or '未命名提案'}",
        workspace_id=workspace_id,
    )

    pain_points = proposal.get("pain_points") or []
    if isinstance(pain_points, list):
        pp_text = "\n".join(f"- {p}" for p in pain_points) or "- （暂无）"
    else:
        pp_text = str(pain_points) or "- （暂无）"

    context = (
        "你正在协助产品经理完善需求提案。当前提案内容如下：\n\n"
        f"标题：{proposal.get('title', '')}\n"
        f"背景：{proposal.get('background', '')}\n"
        f"核心痛点：\n{pp_text}\n"
        f"期望效果：{proposal.get('desired_outcome', '')}\n"
        f"范围说明：{proposal.get('scope_note', '')}\n\n"
        "请与产品经理对话，补充完善上述字段。重点挖掘：业务背景的细节、"
        "痛点的具体表现与影响、期望效果的可衡量目标、范围的边界与假设。"
    )
    await ds.save_message(
        session_id, "system", context,
        event_type="context",
        meta={
            "refine_proposal_id": proposal_id,
            "refine_workspace_id": workspace_id,
        },
    )
    logger.info(
        f"Refine session created: {session_id} for proposal {proposal_id} "
        f"by {current_user.get('username', '?')}"
    )
    return {
        "success": True,
        "session_id": session_id,
        "proposal_id": proposal_id,
        "workspace_id": workspace_id,
    }
