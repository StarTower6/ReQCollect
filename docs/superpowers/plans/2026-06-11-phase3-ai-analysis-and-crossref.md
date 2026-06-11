# Phase 3: AI 主动分析 + 文件交叉引用图 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable AI to auto-analyze workspace files (extract summary, tags, domain) after upload/change, and extend the Wiki cross-reference system to include workspace files.

**Architecture:** Two independent modules — (1) a background analyzer that calls LLM after file change events and stores analysis results in the file JSON index, and (2) an extension of the existing WikiLink DB model (source_type/target_type) to support file→wiki and file→file links with a v2 graph API endpoint.

**Tech Stack:** Python/FastAPI (backend), LangChain @tool (agent), Vue 3 / vis-network (frontend GraphView), Element Plus (tags in file tree)

---

## File Map

| File | Responsibility | Action |
|------|---------------|--------|
| `app/core/workspace_analyzer.py` | Background file analyzer — LLM-based summary/tag extraction | **Create** |
| `app/core/workspace_files.py` | Add `upsert_analysis()` method | **Modify** |
| `app/api/workspace.py` | Trigger analysis after file upload | **Modify** |
| `app/db/models.py` | Extend WikiLink with source_type/target_type/workspace_id | **Modify** |
| `app/db/__init__.py` | Add `save_file_links()` protocol method | **Modify** |
| `app/db/compat.py` | Implement file links in FileDataStore | **Modify** |
| `app/db/repository.py` | Implement file links in MySQLDataStore | **Modify** |
| `app/api/wiki.py` | Extend wiki create/update to resolve [[links]] to files; v2 graph endpoint | **Modify** |
| `app/agent/pm/tools.py` | Enhance `write_workspace_file` to auto-create links from `[[wikilinks]]` in content | **Modify** |
| `reqcollect-web/src/views/wiki/GraphView.vue` | Support file nodes (green) + click to file preview | **Modify** |
| `reqcollect-web/src/components/workspace/FileTreePanel.vue` | Show analysis tags + summary tooltip | **Modify** |
| `tests/test_workspace_analyzer.py` | Tests for analyzer | **Create** |

---

## Task Structure

### Task 1: Create `workspace_analyzer.py` — LLM-based file analyzer

**Files:**
- Create: `app/core/workspace_analyzer.py`
- Modify: `app/core/workspace_files.py` (add `upsert_analysis` method)

- [ ] **Step 1: Add `upsert_analysis` to `WorkspaceFileManager`**

```python
# app/core/workspace_files.py — add to WorkspaceFileManager class

def upsert_analysis(self, relative_path: str, analysis: dict) -> None:
    """Write analysis metadata to the file index entry without touching other fields."""
    safe = Path(relative_path).name
    index = _load_index(self._files_dir)
    for f in index:
        if f["path"] == safe:
            f["analysis"] = analysis
            break
    _save_index(self._files_dir, index)
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_workspace_analyzer.py
import pytest
import tempfile, json, os
from pathlib import Path
from app.core.workspace_analyzer import analyze_workspace_file, _parse_llm_json
from app.core.workspace_files import WorkspaceFileManager, _load_index

TEST_WS_ID = "test_ws_analyze"

@pytest.fixture
def fm():
    from app.config import config
    config.data_dir = tempfile.mkdtemp()
    fm = WorkspaceFileManager(TEST_WS_ID)
    # Upload a simple .md file
    content = b"# 报销审批系统\n\n员工提交报销单，部门经理审批，财务复核，总经理审批。"
    fm.upload_file("报销审批.md", content, "test")
    return fm

def test_parse_llm_json_with_codeblock():
    """_parse_llm_json handles ```json ... ``` wrapped output."""
    raw = '```json\n{"summary": "test", "tags": ["a"], "domain": "d"}\n```'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result["summary"] == "test"

def test_parse_llm_json_plain():
    """_parse_llm_json handles plain JSON without wrapping."""
    raw = '{"summary": "test", "tags": ["a"], "domain": "d"}'
    result = _parse_llm_json(raw)
    assert result is not None

def test_parse_llm_json_invalid():
    """_parse_llm_json returns None on garbage input."""
    assert _parse_llm_json("not json at all") is None
    assert _parse_llm_json("") is None

def test_upsert_analysis(fm):
    """upsert_analysis writes analysis field without changing other fields."""
    analysis = {"summary": "报销系统", "tags": ["报销"], "domain": "审批"}
    fm.upsert_analysis("报销审批.md", analysis)
    info = fm.get_file_info("报销审批.md")
    assert info is not None
    assert info["analysis"] == analysis
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/startower/pm-agent-dev && python -m pytest tests/test_workspace_analyzer.py::test_parse_llm_json_with_codeblock tests/test_workspace_analyzer.py::test_parse_llm_json_plain tests/test_workspace_analyzer.py::test_parse_llm_json_invalid tests/test_workspace_analyzer.py::test_upsert_analysis -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.workspace_analyzer'` and `WorkspaceFileManager has no 'upsert_analysis'`

- [ ] **Step 4: Create `app/core/workspace_analyzer.py`**

```python
"""Background file analyzer — LLM-based summary, tag, domain extraction.

Invoked asynchronously after file upload/write/sync.
Analysis results stored in workspace file index as "analysis" field.
Failures degrade silently — analysis is optional enrichment.
"""

import re
import json
from loguru import logger

# Regex to extract JSON from LLM markdown-wrapped responses
_JSON_IN_MD = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _parse_llm_json(raw: str) -> dict | None:
    """Extract a JSON object from LLM output, tolerating markdown code blocks."""
    if not raw or not raw.strip():
        return None
    m = _JSON_IN_MD.search(raw)
    if m:
        raw = m.group(1)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def analyze_workspace_file(workspace_id: str, file_path: str) -> dict:
    """Analyze file: extract summary, tags, domain via LLM.

    Idempotent: skips if analysis already exists.
    Never raises: returns empty result on any error.
    """
    from app.core.workspace_files import WorkspaceFileManager
    from app.core.llm_factory import llm_factory
    from app.config import config

    fm = WorkspaceFileManager(workspace_id)

    # Skip if already analyzed
    info = fm.get_file_info(file_path)
    if info and info.get("analysis"):
        return info["analysis"]

    try:
        content = fm.read_file(file_path, max_chars=4000)
    except Exception:
        logger.debug(f"[ws analyze] Can't read {workspace_id}/{file_path}")
        fm.upsert_analysis(file_path, {"summary": "", "tags": [], "domain": ""})
        return {"summary": "", "tags": [], "domain": ""}

    text = (content.get("text") or "").strip()
    if not text:
        fm.upsert_analysis(file_path, {"summary": "", "tags": [], "domain": ""})
        return {"summary": "", "tags": [], "domain": ""}

    prompt = (
        "Analyze the following file content. Return ONLY a JSON object:\n"
        '{"summary": "one-sentence summary in Chinese, max 30 characters", '
        '"tags": ["tag1", "tag2", "tag3"], '
        '"domain": "related requirement domain in Chinese (e.g. 审批流系统, 数据治理, 报表)"}\n\n'
        f"File: {file_path}\n\nContent:\n{text[:3000]}"
    )

    try:
        model = llm_factory.create_chat_model(
            model=config.llm_model, temperature=0.1, streaming=False
        )
        response = await model.ainvoke(prompt)
        result_text = response.content if hasattr(response, "content") else str(response)
        result = _parse_llm_json(result_text) or {"summary": "", "tags": [], "domain": ""}
    except Exception as e:
        logger.warning(f"[ws analyze] LLM call failed for {file_path}: {e}")
        result = {"summary": "", "tags": [], "domain": ""}

    fm.upsert_analysis(file_path, result)
    logger.info(f"[ws analyze] {workspace_id}/{file_path}: {result.get('summary')}")
    return result
```

- [ ] **Step 5: Run test to verify passes**

Run: `cd /home/startower/pm-agent-dev && python -m pytest tests/test_workspace_analyzer.py -v`
Expected: 4 passed (parse tests + upsert test)

- [ ] **Step 6: Commit**

```bash
cd /home/startower/pm-agent-dev
git add app/core/workspace_analyzer.py app/core/workspace_files.py tests/test_workspace_analyzer.py
git commit -m "feat: workspace file analyzer — LLM-based summary/tag extraction"
```

---

### Task 2: Trigger analysis after file upload + show tags in file tree

**Files:**
- Modify: `app/api/workspace.py` (trigger analysis after upload)
- Modify: `reqcollect-web/src/components/workspace/FileTreePanel.vue` (show tags + tooltip)

- [ ] **Step 1: Modify `ws_files_upload` to trigger analysis**

```python
# app/api/workspace.py — at top, add import
from app.core.workspace_analyzer import analyze_workspace_file
import asyncio

# In ws_files_upload (lines 165-182), after successful upload:
@router.post("/workspaces/{workspace_id}/files/upload")
async def ws_files_upload(...):
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
            asyncio.ensure_future(analyze_workspace_file(workspace_id, safe_name))
        return {"success": True, "file": result}
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: Modify FileTreePanel.vue to show analysis tags**

In the file row templates (both `ftp-children` file entries and root-level `node.isLeaf` entries), add after the AI badge span:

```html
<!-- After <span v-if="child.source === 'generated'" class="ftp-ai">AI</span> -->
<span v-if="child.analysis?.tags?.length" class="ftp-tags" :title="child.analysis?.summary || ''">
  <span v-for="tag in child.analysis.tags.slice(0, 2)" :key="tag" class="ftp-tag">{{ tag }}</span>
</span>
```

Also in the `v-if="node.isLeaf"` block, same positioning.

Add after the style definitions:
```css
.ftp-tags { display: inline-flex; gap: 2px; flex-shrink: 0; }
.ftp-tag { font-size: 10px; color: #909399; background: #f4f4f5; padding: 0 4px; border-radius: 3px; line-height: 16px; white-space: nowrap; }
```

The `analysis` data needs to flow from `fetchWorkspaceFiles` response. The backend `list_workspace_files` returns index entries which now include `analysis` field. Since `FileTreePanel` builds nodes from `files.value` (which comes from `fetchWorkspaceFiles` response), the `child.analysis` is already available.

- [ ] **Step 3: Build frontend and verify**

Run: `cd reqcollect-web && npx vue-tsc --noEmit 2>&1 | head -20` (check for type errors)

- [ ] **Step 4: Commit**

```bash
cd /home/startower/pm-agent-dev
git add app/api/workspace.py reqcollect-web/src/components/workspace/FileTreePanel.vue
git commit -m "feat: trigger file analysis on upload, show tags in file tree"
```

---

### Task 3: Extend WikiLink data model for file references

**Files:**
- Modify: `app/db/models.py` (WikiLink table)
- Modify: `app/db/__init__.py` (new abstract methods + keep backward compat aliases)
- Modify: `app/db/compat.py` (FileDataStore implementation)
- Modify: `app/db/repository.py` (MySQLDataStore implementation)

- [ ] **Step 1: Modify `WikiLink` model**

```python
# app/db/models.py — replace existing WikiLink class

class WikiLink(Base):
    """Stores [[link]] relationships between wiki pages AND workspace files.

    source_ref + source_type → target_ref + target_type (directed edge).
    source_type / target_type: "wiki" | "file"
    link_type describes the relationship: "reference", "dependency", etc.
    workspace_id ties the link to a workspace for graph queries.
    """

    __tablename__ = "wiki_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    source_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(16), default="wiki")
    target_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(16), default="wiki")
    link_type: Mapped[str] = mapped_column(String(50), default="reference")
    workspace_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
```

- [ ] **Step 2: Update DataStore abstract methods**

```python
# app/db/__init__.py — replace wiki_links section

# ── Wiki Links / File Links ──

@abstractmethod
async def get_wiki_links(self, page_id: str) -> list[dict]:
    """DEPRECATED: Use get_links(source_ref, "wiki"). Kept for backward compat."""

@abstractmethod
async def get_wiki_backlinks(self, page_id: str) -> list[dict]:
    """DEPRECATED: Use get_links(target_ref, "wiki", direction="incoming")."""

@abstractmethod
async def save_wiki_links(
    self, source_page_id: str, target_ids: list[str], link_type: str = "reference"
) -> None:
    """DEPRECATED: Use save_links(). Kept for backward compat."""

@abstractmethod
async def get_links(
    self, workspace_id: str, ref: str, ref_type: str = "wiki",
    direction: str = "outgoing",
) -> list[dict]:
    """Get links from/to a reference.
    direction="outgoing": links where source_ref = ref
    direction="incoming": links where target_ref = ref
    """

@abstractmethod
async def save_links(
    self, workspace_id: str,
    source_ref: str, source_type: str,
    targets: list[tuple[str, str]],  # [(target_ref, target_type), ...]
    link_type: str = "reference",
) -> None:
    """Full-replace: remove old outgoing links from source_ref, insert new ones."""

@abstractmethod
async def get_graph_edges(self, workspace_id: str) -> list[dict]:
    """Get ALL links in a workspace — used by graph endpoint."""

@abstractmethod
async def delete_links_for_ref(self, ref: str, ref_type: str = "wiki") -> None:
    """Remove all links (outgoing + incoming) for a reference."""
```

- [ ] **Step 3: Implement in FileDataStore (`compat.py`)**

```python
# app/db/compat.py — replace existing wiki link methods with new + backward compat aliases

async def get_links(self, workspace_id: str, ref: str, ref_type: str = "wiki",
                    direction: str = "outgoing") -> list[dict]:
    """Get links from/to a reference in a workspace."""
    links_dir = self._base / "wiki" / "_links"
    if not links_dir.exists():
        return []
    result = []
    pattern = f"{ref}--*.json" if direction == "outgoing" else f"*--{ref}.json"
    for f in links_dir.glob(pattern):
        data = self._load_json(f)
        if data and data.get("workspace_id", "") == workspace_id:
            # Normalize old format (source_page_id) to new format (source_ref)
            if "source_page_id" in data and "source_ref" not in data:
                data["source_ref"] = data.pop("source_page_id")
                data["source_type"] = data.get("source_type", "wiki")
            if "target_page_id" in data and "target_ref" not in data:
                data["target_ref"] = data.pop("target_page_id")
                data["target_type"] = data.get("target_type", "wiki")
            result.append(data)
    return result

async def save_links(self, workspace_id: str,
                     source_ref: str, source_type: str,
                     targets: list[tuple[str, str]],
                     link_type: str = "reference") -> None:
    """Full-replace: remove old outgoing links, insert new ones."""
    links_dir = self._base / "wiki" / "_links"
    links_dir.mkdir(parents=True, exist_ok=True)
    # Remove old outgoing links from this source
    for f in list(links_dir.glob(f"{source_ref}--*.json")):
        f.unlink(missing_ok=True)
    # Create new links
    for target_ref, target_type in targets:
        data = {
            "source_ref": source_ref,
            "source_type": source_type,
            "target_ref": target_ref,
            "target_type": target_type,
            "link_type": link_type,
            "workspace_id": workspace_id,
        }
        _FileLock.write_json(links_dir / f"{source_ref}--{target_ref}.json", data)

async def get_graph_edges(self, workspace_id: str) -> list[dict]:
    """Get ALL links in a workspace."""
    links_dir = self._base / "wiki" / "_links"
    if not links_dir.exists():
        return []
    edges = []
    for f in links_dir.glob("*.json"):
        data = self._load_json(f)
        if data and data.get("workspace_id", "") == workspace_id:
            # Normalize old format
            if "source_page_id" in data and "source_ref" not in data:
                data["source_ref"] = data.pop("source_page_id")
                data["source_type"] = data.get("source_type", "wiki")
            if "target_page_id" in data and "target_ref" not in data:
                data["target_ref"] = data.pop("target_page_id")
                data["target_type"] = data.get("target_type", "wiki")
            edges.append({
                "from": f"{data['source_type']}:{data['source_ref']}",
                "to": f"{data['target_type']}:{data['target_ref']}",
                "title": data.get("link_type", "reference"),
            })
    return edges

async def delete_links_for_ref(self, ref: str, ref_type: str = "wiki") -> None:
    """Remove all links (outgoing + incoming) for a reference."""
    links_dir = self._base / "wiki" / "_links"
    if not links_dir.exists():
        return
    for f in list(links_dir.glob(f"{ref}--*.json")):
        f.unlink(missing_ok=True)
    for f in list(links_dir.glob(f"*--{ref}.json")):
        f.unlink(missing_ok=True)

# ── Backward compat aliases ──
async def get_wiki_links(self, page_id: str) -> list[dict]:
    return await self.get_links("", page_id, "wiki", "outgoing")

async def get_wiki_backlinks(self, page_id: str) -> list[dict]:
    return await self.get_links("", page_id, "wiki", "incoming")

async def save_wiki_links(
    self, source_page_id: str, target_ids: list[str], link_type: str = "reference"
) -> None:
    targets = [(tid, "wiki") for tid in target_ids]
    await self.save_links("", source_page_id, "wiki", targets, link_type)
```

- [ ] **Step 4: Implement in MySQLDataStore (`repository.py`)**

Add `source_type`/`target_type`/`workspace_id` column awareness to existing methods, and implement new methods:

```python
# app/db/repository.py — add new methods, update old ones as thin wrappers

async def get_graph_edges(self, workspace_id: str) -> list[dict]:
    """Get ALL links in a workspace for graph visualization."""
    async with await self._get_session() as s:
        result = await s.execute(
            select(WikiLink).where(WikiLink.workspace_id == workspace_id)
        )
        links = result.scalars().all()
        return [{
            "from": f"{link.source_type}:{link.source_ref}",
            "to": f"{link.target_type}:{link.target_ref}",
            "title": link.link_type,
        } for link in links]

async def get_links(self, workspace_id: str, ref: str, ref_type: str = "wiki",
                    direction: str = "outgoing") -> list[dict]:
    async with await self._get_session() as s:
        if direction == "outgoing":
            where = and_(WikiLink.source_ref == ref, WikiLink.source_type == ref_type)
        else:
            where = and_(WikiLink.target_ref == ref, WikiLink.target_type == ref_type)
        if workspace_id:
            where = and_(where, WikiLink.workspace_id == workspace_id)
        stmt = select(WikiLink).where(where)
        result = await s.execute(stmt)
        return [link.to_dict() for link in result.scalars().all()]

async def save_links(self, workspace_id: str,
                     source_ref: str, source_type: str,
                     targets: list[tuple[str, str]],
                     link_type: str = "reference") -> None:
    async with await self._get_session() as s:
        # Remove old outgoing
        await s.execute(
            delete(WikiLink).where(
                WikiLink.source_ref == source_ref,
                WikiLink.source_type == source_type,
                WikiLink.workspace_id == workspace_id,
            )
        )
        # Insert new
        for target_ref, target_type in targets:
            s.add(WikiLink(
                source_ref=source_ref, source_type=source_type,
                target_ref=target_ref, target_type=target_type,
                link_type=link_type, workspace_id=workspace_id,
            ))
        await s.commit()

async def delete_links_for_ref(self, ref: str, ref_type: str = "wiki") -> None:
    async with await self._get_session() as s:
        await s.execute(
            delete(WikiLink).where(
                or_(
                    and_(WikiLink.source_ref == ref, WikiLink.source_type == ref_type),
                    and_(WikiLink.target_ref == ref, WikiLink.target_type == ref_type),
                )
            )
        )
        await s.commit()
```

- [ ] **Step 5: Run existing tests to verify no regression**

Run: `cd /home/startower/pm-agent-dev && python -m pytest tests/test_workspace_files.py -v`
Expected: all existing tests pass

- [ ] **Step 6: Commit**

```bash
cd /home/startower/pm-agent-dev
git add app/db/models.py app/db/__init__.py app/db/compat.py app/db/repository.py
git commit -m "feat: extend WikiLink model for file references (source_type/target_type)"
```

---

### Task 4: Update wiki API to link files + v2 graph endpoint

**Files:**
- Modify: `app/api/wiki.py` (update wiki create/update to resolve [[links]] → files; add v2 graph endpoint resolving file nodes)

- [ ] **Step 1: Update wiki create/update to resolve file links**

In `wiki_create` and `wiki_update` handlers, after parsing [[links]] from content, the current logic resolves link titles to wiki page IDs. Expand it to also check workspace files:

```python
# app/api/wiki.py — in wiki_create / wiki_update, after extracting link_titles from content:

# Resolve [[links]] to (target_ref, target_type)
resolved_targets = []
for title in link_titles:
    # Try wiki page match
    page = await ds.resolve_wiki_title(workspace_id, title)
    if page:
        resolved_targets.append((page["id"], "wiki"))
    else:
        # Try workspace file match
        files = await ds.list_workspace_files(workspace_id, pattern=f"*{title}*", max_results=5)
        if any(f["path"] == title for f in files):
            resolved_targets.append((title, "file"))
        elif any(title in f["path"] for f in files):
            # Fuzzy match: use first match
            resolved_targets.append((files[0]["path"], "file"))

# Replace old save_wiki_links call with:
if resolved_targets:
    await ds.save_links(workspace_id, page_id, "wiki", resolved_targets)
else:
    # Clear existing links
    await ds.save_links(workspace_id, page_id, "wiki", [])
```

- [ ] **Step 2: Add v2 graph endpoint**

```python
# app/api/wiki.py

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

    # Get all graph edges
    edges = await ds.get_graph_edges(workspace_id)

    # Collect file nodes referenced in edges
    for edge in edges:
        from_parts = edge["from"].split(":", 1)
        to_parts = edge["to"].split(":", 1)
        if len(from_parts) == 2 and from_parts[0] == "file" and edge["from"] not in nodes:
            nodes[edge["from"]] = {
                "id": edge["from"],
                "label": from_parts[1].split("/")[-1],  # basename
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
```

- [ ] **Step 3: Commit**

```bash
cd /home/startower/pm-agent-dev
git add app/api/wiki.py
git commit -m "feat: [[links]] resolve to files + v2 graph endpoint with file nodes"
```

---

### Task 5: Enhance agent write to auto-create file links

**Files:**
- Modify: `app/agent/pm/tools.py` (enhance `write_workspace_file`)

- [ ] **Step 1: Enhance `write_workspace_file` tool**

```python
# app/agent/pm/tools.py — in write_workspace_file function

@tool
def write_workspace_file(
    workspace_id: str,
    file_path: str,
    content: str,
) -> str:
    """在工作区中创建或更新文件。
    用于 AI 生成的产出——分析报告、需求总结、会议纪要等。
    文件会自动写入工作区的 _generated/ 子目录。
    如果内容中包含 [[链接]] 语法，会自动建立文件引用关系。

    Args:
        workspace_id: 工作区 ID
        file_path: 文件名（如 "分析报告-20260610.md"）
        content: 文件内容

    Returns:
        写入成功的消息
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        result = fm.write_file(file_path, content)

        # Parse [[links]] in content and create file references
        import re
        link_refs = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content)
        if link_refs and _datastore:
            targets = []
            all_files = fm.list_files()
            for title in link_refs:
                title = title.strip()
                # Try wiki page (if datastore supports it)
                try:
                    import asyncio
                    page = asyncio.run(_datastore.resolve_wiki_title(workspace_id, title))
                    if page:
                        targets.append((page["id"], "wiki"))
                        continue
                except (AttributeError, Exception):
                    pass
                # Try workspace file
                if any(f["path"] == title for f in all_files):
                    targets.append((title, "file"))
            if targets:
                import asyncio
                asyncio.run(_datastore.save_links(
                    workspace_id, file_path, "file", targets
                ))

        return f"文件已写入工作区：{result['path']} ({_fmt_size(result['size'])})"
    except Exception as e:
        return f"写入文件失败：{e}"
```

- [ ] **Step 2: Commit**

```bash
cd /home/startower/pm-agent-dev
git add app/agent/pm/tools.py
git commit -m "feat: write_workspace_file auto-creates cross-references from [[links]]"
```

---

### Task 6: Update GraphView for file nodes

**Files:**
- Modify: `reqcollect-web/src/views/wiki/GraphView.vue`

- [ ] **Step 1: Update GraphView.vue**

Wait — the current GraphView props are `workspaceId` but it uses the old `/api/wiki/graph/{workspace_id}` endpoint. The API now returns the v2 format with file nodes. Update the rendering to support `type: "file"` nodes.

```typescript
// In the script, after dynamic import of vis-network:

function nodeColor(type: string): string {
  return type === 'file' ? '#67c23a' : '#409eff'
}

// In the nodes DataSet creation:
nodes.add(
  graph.nodes.map((n: any) => ({
    id: n.id,
    label: n.label,
    title: `${n.title} (${n.type === 'file' ? '文件' : 'Wiki'})`,
    color: { background: nodeColor(n.type), border: nodeColor(n.type) },
    value: n.value || 1,
    group: n.type,
  }))
)

// In the click handler:
network.on('click', (params: any) => {
  const nodeId = params.nodes?.[0]
  if (!nodeId) return
  const node = graph.nodes.find((n: any) => n.id === nodeId)
  if (!node) return
  if (node.type === 'wiki') {
    router.push(`/workspace/${props.workspaceId}/wiki/${nodeId.replace('wiki:', '')}`)
  } else {
    // File node — open file preview (emit event or navigate)
    // Currently no file preview route; open in workspace detail
    router.push(`/workspace/${props.workspaceId}`)
  }
})
```

- [ ] **Step 2: Verify no TypeScript errors**

Run: `cd reqcollect-web && npx vue-tsc --noEmit 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
cd /home/startower/pm-agent-dev
git add reqcollect-web/src/views/wiki/GraphView.vue
git commit -m "feat: GraphView supports file nodes (green) with separate click handling"
```

---

## Verification

### Module 1 — Agent 主动感知
1. **Upload a file via workspace API**: POST file to `/api/workspaces/{ws_id}/files/upload` → file appears in list → analysis runs in background (check logs)
2. **Check analysis stored**: `GET /api/workspaces/{ws_id}/files` → file entry has `analysis` field with `summary`, `tags`, `domain`
3. **Frontend file tree**: Tags show as small gray pills next to file names, hovering shows summary tooltip

### Module 2 — 文件交叉引用图
1. **Wiki page with `[[file.md]]`**: Create/update wiki page containing `[[existing_file.md]]` → link stored in WikiLink table with `target_type="file"`
2. **Graph endpoint**: `GET /api/wiki/graph/{ws_id}` → file nodes appear with `type: "file"` and green color in GraphView
3. **Agent write with `[[links]]`**: Send file content with `[[other_file.md]]` via agent → file links created automatically
4. **Backlinks**: File referenced by wiki page shows in backlinks list

### End-to-end
1. Create workspace → Upload a .md file → Analysis runs → Tags visible in file tree
2. Create wiki page → Use `[[filename.md]]` to reference the file → Graph shows file node in green
3. Agent writes a report → Content references another file → Graph auto-updates

### GitNexus check
Before final commit, run: `cd /home/startower/pm-agent-dev && npx gitnexus analyze`
