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

    # Parse [[links]] from content and save links (wiki + file)
    if body.content:
        titles = set()
        for match in WIKILINK_RE.finditer(body.content):
            title = match.group(1).strip()
            if title:
                titles.add(title)
        resolved_targets = []
        if titles:
            # Resolve titles to wiki page IDs
            all_pages = await ds.list_wiki_pages(body.workspace_id)
            title_to_id = {p["title"]: p["id"] for p in all_pages}
            for t in titles:
                if t in title_to_id:
                    resolved_targets.append((title_to_id[t], "wiki"))
                else:
                    # Try workspace file match
                    try:
                        files = await ds.list_workspace_files(
                            body.workspace_id, pattern=f"*{t}*", max_results=5
                        )
                        if any(f["path"] == t for f in files):
                            resolved_targets.append((t, "file"))
                        elif files and any(t in f["path"] for f in files):
                            resolved_targets.append((files[0]["path"], "file"))
                    except Exception:
                        pass
        await ds.save_links(body.workspace_id, page["id"], "wiki", resolved_targets)

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

    # Resolve user IDs to display names
    created_by = page.get("created_by", "")
    updated_by = page.get("updated_by", "")
    if created_by:
        u = await ds.get_user_by_id(created_by)
        page["created_by_name"] = u["display_name"] if u else created_by
    else:
        page["created_by_name"] = ""
    if updated_by and updated_by != created_by:
        u = await ds.get_user_by_id(updated_by)
        page["updated_by_name"] = u["display_name"] if u else updated_by
    elif updated_by:
        page["updated_by_name"] = page.get("created_by_name", "")

    # Fetch backlinks (pages that link TO this page)
    backlinks = await ds.get_wiki_backlinks(page_id)
    backlink_pages = []
    for bl in backlinks:
        src = await ds.get_wiki_page(bl["source_ref"])
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

    # Parse [[links]] from updated content and save links (wiki + file)
    if "content" in kwargs:
        content = kwargs["content"]
        titles = set()
        for match in WIKILINK_RE.finditer(content):
            title = match.group(1).strip()
            if title:
                titles.add(title)
        resolved_targets = []
        if titles:
            all_pages = await ds.list_wiki_pages(page["workspace_id"])
            title_to_id = {p["title"]: p["id"] for p in all_pages}
            for t in titles:
                if t in title_to_id:
                    resolved_targets.append((title_to_id[t], "wiki"))
                else:
                    # Try workspace file match
                    try:
                        files = await ds.list_workspace_files(
                            page["workspace_id"], pattern=f"*{t}*", max_results=5
                        )
                        if any(f["path"] == t for f in files):
                            resolved_targets.append((t, "file"))
                        elif files and any(t in f["path"] for f in files):
                            resolved_targets.append((files[0]["path"], "file"))
                    except Exception:
                        pass
        await ds.save_links(page["workspace_id"], page_id, "wiki", resolved_targets)

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


# ── Graph ──


@router.get("/wiki/graph/{workspace_id}")
async def wiki_graph(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get graph data for a workspace: wiki nodes + file nodes + edges."""
    ds = _ds()
    pages = await ds.list_wiki_pages(workspace_id)

    # Build wiki nodes
    nodes = {}
    for p in pages:
        out_links = await ds.get_links(workspace_id, p["id"], "wiki", "outgoing")
        nodes[p["id"]] = {
            "id": f"wiki:{p['id']}",
            "label": p["title"],
            "title": p["title"],
            "type": "wiki",
            "value": max(len(out_links), 1),
        }

    # Get all graph edges from the workspace
    edges = await ds.get_graph_edges(workspace_id)

    # Collect file nodes referenced in edges
    for edge in edges:
        from_parts = edge["from"].split(":", 1)
        to_parts = edge["to"].split(":", 1)
        if len(from_parts) == 2 and from_parts[0] == "file" and edge["from"] not in nodes:
            nodes[edge["from"]] = {
                "id": edge["from"],
                "label": from_parts[1].split("/")[-1],
                "title": from_parts[1],
                "type": "file",
                "value": 1,
            }
        if len(to_parts) == 2 and to_parts[0] == "file" and edge["to"] not in nodes:
            nodes[edge["to"]] = {
                "id": edge["to"],
                "label": to_parts[1].split("/")[-1],
                "title": to_parts[1],
                "type": "file",
                "value": 1,
            }

    return {"success": True, "graph": {"nodes": list(nodes.values()), "edges": edges}}
