"""Wiki page API endpoints.

Routes:
  GET    /api/wiki              — list wiki pages (query: workspace_id)
  POST   /api/wiki              — create wiki page
  GET    /api/wiki/{page_id}    — get wiki page detail
  PATCH  /api/wiki/{page_id}    — update wiki page
  DELETE /api/wiki/{page_id}    — delete wiki page
  GET    /api/wiki/titles/search — search wiki page titles for [[autocomplete]]
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel

from app.core.auth import get_current_user


WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


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

    # Parse [[links]] from content and save wiki_links
    if body.content:
        titles = set()
        for match in WIKILINK_RE.finditer(body.content):
            title = match.group(1).strip()
            if title:
                titles.add(title)
        all_pages = await ds.list_wiki_pages(body.workspace_id)
        title_to_id = {p["title"]: p["id"] for p in all_pages}
        target_ids = [title_to_id[t] for t in titles if t in title_to_id]
        if target_ids:
            await ds.save_wiki_links(page["id"], target_ids)

    logger.info(f"Wiki page created: '{page['title']}' by {current_user['username']}")
    return {"success": True, "page": page}


@router.get("/wiki/titles/search")
async def wiki_titles_search(
    q: str = Query("", description="Search query"),
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: dict = Depends(get_current_user),
):
    """Search wiki page titles in a workspace (for [[autocomplete]])."""
    ds = _ds()
    pages = await ds.list_wiki_pages(workspace_id)
    if q:
        ql = q.lower()
        pages = [p for p in pages if ql in p["title"].lower()]
    return {
        "success": True,
        "titles": [{"id": p["id"], "title": p["title"]} for p in pages[:20]],
    }


@router.get("/wiki/{page_id}")
async def wiki_get(
    page_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a wiki page by ID, including backlinks."""
    ds = _ds()
    page = await ds.get_wiki_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")

    # Fetch backlinks (pages that link TO this page)
    backlinks = await ds.get_wiki_backlinks(page_id)
    backlink_pages = []
    for bl in backlinks:
        src = await ds.get_wiki_page(bl["source_page_id"])
        if src:
            backlink_pages.append({
                "id": src["id"],
                "title": src["title"],
            })

    return {"success": True, "page": page, "backlinks": backlink_pages}


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

    # Parse [[links]] from updated content and save wiki_links
    if "content" in kwargs:
        content = kwargs["content"]
        titles = set()
        for match in WIKILINK_RE.finditer(content):
            title = match.group(1).strip()
            if title:
                titles.add(title)
        all_pages = await ds.list_wiki_pages(page["workspace_id"])
        title_to_id = {p["title"]: p["id"] for p in all_pages}
        target_ids = [title_to_id[t] for t in titles if t in title_to_id]
        if target_ids:
            await ds.save_wiki_links(page_id, target_ids)
        else:
            # Clear links if no [[links]] remain
            await ds.save_wiki_links(page_id, [])

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
    await ds.delete_wiki_links_for_page(page_id)
    await ds.delete_wiki_page(page_id)
    logger.info(f"Wiki page deleted: '{page.get('title', page_id)}' by {current_user['username']}")
    return {"success": True}


# ── Graph ──


@router.get("/wiki/graph/{workspace_id}")
async def wiki_graph(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get graph data for a workspace: nodes=pages, edges=wiki_links."""
    ds = _ds()
    pages = await ds.list_wiki_pages(workspace_id)
    nodes = {}
    for p in pages:
        out_links = await ds.get_wiki_links(p["id"])
        # Count outgoing links for this node
        connected = len(out_links)
        nodes[p["id"]] = {
            "id": p["id"],
            "label": p["title"],
            "title": p["title"],
            "group": "page",
            "value": max(connected, 1),
        }
    edges = []
    seen = set()
    for p in pages:
        out_links = await ds.get_wiki_links(p["id"])
        for link in out_links:
            edge_key = f"{link['source_page_id']}-{link['target_page_id']}"
            if edge_key not in seen and link["target_page_id"] in nodes:
                seen.add(edge_key)
                edges.append({
                    "from": link["source_page_id"],
                    "to": link["target_page_id"],
                    "title": "引用",
                })
    return {
        "success": True,
        "graph": {
            "nodes": list(nodes.values()),
            "edges": edges,
        },
    }
