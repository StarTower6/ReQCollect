"""Wiki page API endpoints.

Routes:
  GET    /api/wiki              — list wiki pages (query: workspace_id)
  POST   /api/wiki              — create wiki page
  GET    /api/wiki/{page_id}    — get wiki page detail
  PATCH  /api/wiki/{page_id}    — update wiki page
  DELETE /api/wiki/{page_id}    — delete wiki page
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel

from app.core.auth import get_current_user


def _ds():
    from app.main import get_datastore
    d = get_datastore()
    if d is None:
        raise RuntimeError("DataStore not initialized")
    return d


router = APIRouter()


# ── Models ──


class WikiPageCreate(BaseModel):
    workspace_id: str
    title: str
    content: str = ""


class WikiPageUpdate(BaseModel):
    title: str = ""
    content: str = ""


# ── Routes ──


@router.get("/wiki")
async def wiki_list(
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: dict = Depends(get_current_user),
):
    """List all wiki pages in a workspace."""
    ds = _ds()
    pages = await ds.list_wiki_pages(workspace_id)
    return {"success": True, "pages": pages, "total": len(pages)}


@router.post("/wiki", status_code=201)
async def wiki_create(
    body: WikiPageCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new wiki page."""
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    ds = _ds()
    page = await ds.create_wiki_page(
        workspace_id=body.workspace_id,
        title=body.title.strip(),
        content=body.content,
        created_by=current_user["id"],
    )
    logger.info(f"Wiki page created: '{page['title']}' by {current_user['username']}")
    return {"success": True, "page": page}


@router.get("/wiki/{page_id}")
async def wiki_get(
    page_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a wiki page by ID."""
    ds = _ds()
    page = await ds.get_wiki_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return {"success": True, "page": page}


@router.patch("/wiki/{page_id}")
async def wiki_update(
    page_id: str,
    body: WikiPageUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update wiki page fields."""
    ds = _ds()
    kwargs = body.model_dump(exclude_unset=True)
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    kwargs["updated_by"] = current_user["id"]
    page = await ds.update_wiki_page(page_id, **kwargs)
    if page is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    logger.info(f"Wiki page updated: '{page['title']}'")
    return {"success": True, "page": page}


@router.delete("/wiki/{page_id}")
async def wiki_delete(
    page_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a wiki page."""
    ds = _ds()
    page = await ds.get_wiki_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    await ds.delete_wiki_page(page_id)
    logger.info(f"Wiki page deleted: '{page.get('title', page_id)}' by {current_user['username']}")
    return {"success": True}
