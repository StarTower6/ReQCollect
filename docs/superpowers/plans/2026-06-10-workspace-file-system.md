# 工作区文件系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 MiningAgent 能感知工作区文件并进行分析，用户可通过前端上传/管理工作区文件

**Architecture:** 新增 `WorkspaceFileManager` 模块独立处理文件存储和索引（JSON on disk，不依赖 DataStore 后端），6 个 Agent 工具注册到现有 MiningAgent，前端 WorkspaceDetail 新增「文件」Tab

**Tech Stack:** Python 3.11+ (pathlib, python-docx, openpyxl), Vue 3 (Element Plus), FastAPI

---

### Task 1: 创建 WorkspaceFileManager 核心模块

**Files:**
- Create: `app/core/workspace_files.py`
- Modify: `app/core/file_handler.py`

**app/core/file_handler.py:17** — 扩展允许上传的文件类型：

```python
# 原:
ALLOWED_EXTENSIONS = {".md"}
# 改为:
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".docx", ".xlsx"}
```

**app/core/workspace_files.py** — 新建文件，包含：
- Office 解析辅助函数（parse_docx, parse_xlsx）
- 文件类型检测（is_text_file, is_office_file, detect_file_type）
- 路径安全校验 `_validate_file_path`
- JSON 索引的读写 `_load_index`, `_save_index`
- **WorkspaceFileManager** 类：list / read / search / write / upload / delete / info

```python
"""Workspace file management — index, upload, read, search, Office parsing.

Independent of DataStore backend: file index is always JSON on disk.
FileManager operates on the workspace's files/ directory under data_dir.
"""

from __future__ import annotations

import json
import fnmatch
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import config
from app.core.file_handler import (
    MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS,
    FileValidationError,
    decode_content,
    validate_upload,
)

# ── Office parsing (optional) ──

_HAS_DOCX = False
try:
    import docx as _docx_module
    _HAS_DOCX = True
except ImportError:
    pass


def parse_docx(file_path: str | Path) -> str:
    if not _HAS_DOCX:
        raise RuntimeError("python-docx not installed. Run: pip install python-docx")
    doc = _docx_module.Document(str(file_path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_xlsx(file_path: str | Path) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(str(file_path), read_only=True)
    lines = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        lines.append(f"=== {sheet_name} ===")
        for row in ws.iter_rows(values_only=True):
            row_text = " | ".join(str(c) if c is not None else "" for c in row)
            if row_text.strip(" |"):
                lines.append(row_text)
    wb.close()
    return "\n".join(lines)


def is_text_file(ext: str) -> bool:
    return ext in ("md", "txt", "json", "yaml", "yml")


def _validate_file_path(workspace_dir: Path, relative_path: str) -> Path:
    resolved = (workspace_dir / relative_path).resolve()
    if not str(resolved).startswith(str(workspace_dir.resolve())):
        raise FileValidationError("Path traversal detected")
    return resolved


def _index_path(files_dir: Path) -> Path:
    return files_dir / "_index.json"


def _load_index(files_dir: Path) -> list[dict]:
    p = _index_path(files_dir)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(files_dir: Path, index: list[dict]) -> None:
    p = _index_path(files_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


class WorkspaceFileManager:
    """Manages files within a single workspace. File path: <data_dir>/workspaces/<ws_id>/files/"""

    def __init__(self, workspace_id: str):
        ws_dir = Path(config.data_dir) / "workspaces" / workspace_id
        self._files_dir = ws_dir / "files"
        self._uploads_dir = self._files_dir / "uploads"
        self._generated_dir = self._files_dir / "_generated"

    # ── public API ──

    def list_files(self, pattern: str = "*", max_results: int = 50) -> list[dict]:
        index = _load_index(self._files_dir)
        if pattern != "*":
            matched = [f for f in index if fnmatch.fnmatch(f["path"], pattern)]
        else:
            matched = list(index)
        matched.sort(key=lambda f: f.get("uploaded_at", ""), reverse=True)
        return matched[:max_results]

    def get_file_info(self, relative_path: str) -> dict | None:
        safe = Path(relative_path).name
        for f in _load_index(self._files_dir):
            if f["path"] == safe:
                return f
        return None

    def read_file(self, relative_path: str, max_chars: int = 8000) -> dict:
        entry = self.get_file_info(relative_path)
        if entry is None:
            raise FileNotFoundError(f"File not found: {relative_path}")

        ext = entry.get("type", "")
        if entry["source"] in ("upload", "generated"):
            base = self._uploads_dir if entry["source"] == "upload" else self._generated_dir
            file_path = _validate_file_path(base, relative_path)
        elif entry.get("abs_path"):
            file_path = Path(entry["abs_path"])
            if not file_path.exists():
                raise FileNotFoundError(f"Linked file not found: {file_path}")
        else:
            raise FileNotFoundError(f"Cannot resolve file: {relative_path}")

        size = file_path.stat().st_size
        if is_text_file(ext):
            text = file_path.read_text(encoding="utf-8", errors="replace")
        elif ext == "docx":
            text = parse_docx(file_path)
        elif ext == "xlsx":
            text = parse_xlsx(file_path)
        else:
            text = file_path.read_text(encoding="utf-8", errors="replace")

        truncated = False
        if len(text) > max_chars:
            text = text[:max_chars]
            truncated = True
        return {"path": relative_path, "text": text, "size": size, "type": ext, "truncated": truncated}

    def read_file_section(self, relative_path: str, start: int = 1, end: int = 100) -> dict:
        content = self.read_file(relative_path, max_chars=10 * 1024 * 1024)
        lines = content["text"].split("\n")
        return {
            "path": relative_path,
            "lines": lines[start - 1 : end],
            "start_line": start, "end_line": min(end, len(lines)),
            "total_lines": len(lines),
        }

    def search_files(self, query: str, file_pattern: str = "*.md", max_results: int = 10) -> list[dict]:
        results = []
        for entry in _load_index(self._files_dir):
            if not fnmatch.fnmatch(entry["path"], file_pattern):
                continue
            try:
                content = self.read_file(entry["path"], max_chars=100 * 1024)
            except (FileNotFoundError, RuntimeError):
                continue
            lines = content["text"].split("\n")
            matches = [(i + 1, l.strip()[:200]) for i, l in enumerate(lines) if query.lower() in l.lower()]
            if matches:
                results.append({
                    "path": entry["path"],
                    "type": entry.get("type", ""),
                    "matches": [{"line": ln, "text": txt} for ln, txt in matches[:10]],
                    "match_count": len(matches),
                })
            if len(results) >= max_results:
                break
        return results

    def write_file(self, relative_path: str, content: str) -> dict:
        safe_name = Path(relative_path).name
        dest = self._generated_dir / safe_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

        self._upsert_index({
            "path": safe_name,
            "size": len(content.encode("utf-8")),
            "type": Path(safe_name).suffix.lower().lstrip("."),
            "source": "generated",
            "uploaded_at": _now(),
            "uploaded_by": "agent",
            "summary": content[:100].replace("\n", " "),
        })
        logger.info(f"[ws files] Generated: {safe_name}")
        return {"path": safe_name, "size": len(content)}

    def upload_file(self, filename: str, content: bytes, uploaded_by: str = "") -> dict:
        validate_upload(filename, content)
        safe_name = Path(filename).name
        ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else "bin"
        dest = self._uploads_dir / safe_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not (dest.exists() and dest.stat().st_size == len(content)):
            dest.write_bytes(content)

        # Parse for summary
        text = decode_content(content) if is_text_file(ext) else ""
        if ext == "docx" and _HAS_DOCX:
            try:
                text = parse_docx(dest)
            except RuntimeError:
                text = ""
        elif ext == "xlsx":
            try:
                text = parse_xlsx(dest)
            except Exception:
                text = ""
        summary = text[:100].replace("\n", " ") if text else ""
        if not summary:
            summary = f"Uploaded {filename}"

        self._upsert_index({
            "path": safe_name,
            "size": len(content),
            "type": ext,
            "source": "upload",
            "uploaded_at": _now(),
            "uploaded_by": uploaded_by,
            "summary": summary,
        })
        return {"path": safe_name, "size": len(content), "type": ext}

    def delete_file(self, relative_path: str) -> bool:
        safe_name = Path(relative_path).name
        entries = [f for f in _load_index(self._files_dir) if f["path"] == safe_name]
        if not entries:
            return False
        index = [f for f in _load_index(self._files_dir) if f["path"] != safe_name]
        _save_index(self._files_dir, index)

        entry = entries[0]
        if entry["source"] == "upload":
            target = self._uploads_dir / safe_name
        elif entry["source"] == "generated":
            target = self._generated_dir / safe_name
        else:
            target = None
        if target and target.exists():
            target.unlink()
        return True

    def get_info(self) -> dict:
        index = _load_index(self._files_dir)
        types, sources = {}, {}
        for f in index:
            types[f.get("type", "?")] = types.get(f.get("type", "?"), 0) + 1
            sources[f.get("source", "?")] = sources.get(f.get("source", "?"), 0) + 1
        return {"file_count": len(index), "by_type": types, "by_source": sources,
                "files": [{"path": f["path"], "type": f.get("type", ""), "size": f.get("size", 0),
                           "source": f.get("source", ""), "uploaded_at": f.get("uploaded_at", ""),
                           "summary": f.get("summary", "")} for f in index]}

    def _upsert_index(self, entry: dict) -> None:
        index = _load_index(self._files_dir)
        index = [f for f in index if f["path"] != entry["path"]]
        index.append(entry)
        _save_index(self._files_dir, index)
```

- [ ] **Step 1: 修改 file_handler.py 的 ALLOWED_EXTENSIONS**

Edit `app/core/file_handler.py` line 17:
```python
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".docx", ".xlsx"}
```

- [ ] **Step 2: 创建 app/core/workspace_files.py**

Write the full file above.

- [ ] **Step 3: 验证导入**

Run: `cd /home/startower/pm-agent-dev && python3 -c "from app.core.workspace_files import WorkspaceFileManager; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add app/core/file_handler.py app/core/workspace_files.py
git commit -m "feat: add WorkspaceFileManager module for workspace file operations"
```

---

### Task 2: DataStore 抽象方法 + 文件 API 端点

**Files:**
- Modify: `app/db/__init__.py` (添加 workspace file 抽象方法)
- Modify: `app/db/compat.py` (FileDataStore 实现)
- Modify: `app/db/repository.py` (MySQLDataStore 实现)
- Modify: `app/api/workspace.py` (添加文件 CRUD 端点)
- Modify: `app/api/workspace.py` (添加 import)

在 `app/db/__init__.py` 中 Workspaces 区域后添加：

```python
    # ── Workspace Files ──

    @abstractmethod
    async def list_workspace_files(
        self, workspace_id: str, pattern: str = "*", max_results: int = 50
    ) -> list[dict]:
        """List files in workspace."""

    @abstractmethod
    async def add_workspace_file(
        self, workspace_id: str, filename: str, content: bytes, uploaded_by: str = ""
    ) -> dict:
        """Upload and index a file in the workspace."""

    @abstractmethod
    async def read_workspace_file(
        self, workspace_id: str, file_path: str, max_chars: int = 8000
    ) -> dict:
        """Read file content."""

    @abstractmethod
    async def remove_workspace_file(
        self, workspace_id: str, file_path: str
    ) -> bool:
        """Delete a file from workspace."""

    @abstractmethod
    async def search_workspace_files(
        self, workspace_id: str, query: str,
        file_pattern: str = "*.md", max_results: int = 10
    ) -> list[dict]:
        """Full-text search in workspace files."""

    @abstractmethod
    async def write_workspace_file(
        self, workspace_id: str, file_path: str, content: str
    ) -> dict:
        """Write AI-generated file to workspace."""

    @abstractmethod
    async def get_workspace_files_info(self, workspace_id: str) -> dict:
        """Get workspace file overview."""
```

在 `app/db/compat.py` 的 FileDataStore 类中添加：

```python
    # ── Workspace Files ──

    async def list_workspace_files(self, workspace_id: str, pattern: str = "*", max_results: int = 50) -> list[dict]:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).list_files(pattern, max_results)

    async def add_workspace_file(self, workspace_id: str, filename: str, content: bytes, uploaded_by: str = "") -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).upload_file(filename, content, uploaded_by)

    async def read_workspace_file(self, workspace_id: str, file_path: str, max_chars: int = 8000) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).read_file(file_path, max_chars)

    async def remove_workspace_file(self, workspace_id: str, file_path: str) -> bool:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).delete_file(file_path)

    async def search_workspace_files(self, workspace_id: str, query: str, file_pattern: str = "*.md", max_results: int = 10) -> list[dict]:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).search_files(query, file_pattern, max_results)

    async def write_workspace_file(self, workspace_id: str, file_path: str, content: str) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).write_file(file_path, content)

    async def get_workspace_files_info(self, workspace_id: str) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).get_info()
```

在 `app/db/repository.py` 的 MySQLDataStore 中添加完全相同的方法（内容一致）。

在 `app/api/workspace.py` 中添加文件端点：

```python
# 在文件顶部的 import 区域补充
from fastapi import UploadFile, File, Query
from app.core.file_handler import FileValidationError

# 在 ws_sessions 之后添加

@router.get("/workspaces/{workspace_id}/files")
async def ws_files_list(
    workspace_id: str,
    pattern: str = Query(default="*"),
    max_results: int = Query(default=50, le=200),
    current_user: dict = Depends(get_current_user),
):
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
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    content = await file.read()
    filename = file.filename or "untitled"
    try:
        result = await ds.add_workspace_file(workspace_id, filename, content, current_user["id"])
        return {"success": True, "file": result}
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workspaces/{workspace_id}/files/{path:path}")
async def ws_files_read(
    workspace_id: str,
    path: str,
    max_chars: int = Query(default=8000, le=100000),
    current_user: dict = Depends(get_current_user),
):
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
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    deleted = await ds.remove_workspace_file(workspace_id, path)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    return {"success": True}


@router.get("/workspaces/{workspace_id}/files/info")
async def ws_files_info(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    info = await ds.get_workspace_files_info(workspace_id)
    return {"success": True, "info": info}
```

- [ ] **Step 1: DataStore 抽象**

Edit `app/db/__init__.py` to add workspace file abstract methods after line ~248 (end of Wiki Links section, before Audit).

- [ ] **Step 2: FileDataStore 实现**

Edit `app/db/compat.py` — 在 FileDataStore 类末尾（delete_workspace 之后）添加 workspace file 方法。

- [ ] **Step 3: MySQLDataStore 实现**

Edit `app/db/repository.py` — 在 MySQLDataStore 类末尾添加同样的方法。

- [ ] **Step 4: Workspace API 端点**

Edit `app/api/workspace.py` — 添加 import + 5 个新端点。

- [ ] **Step 5: 验证路由加载**

Run: `cd /home/startower/pm-agent-dev && python3 -c "from app.main import app; routes = [r.path for r in app.routes]; print([r for r in routes if 'files' in r])"`
Expected: 能看到 /workspaces/{id}/files 系列路由

- [ ] **Step 6: Commit**

```bash
git add app/db/__init__.py app/db/compat.py app/db/repository.py app/api/workspace.py
git commit -m "feat: add workspace file DataStore methods and REST API endpoints"
```

---

### Task 3: Agent 工具注册

**Files:**
- Modify: `app/agent/pm/tools.py` (新增 6 个文件工具)
- Modify: `app/agent/pm/phase1/mining_agent.py` (注册工具)

在 `app/agent/pm/tools.py` 末尾添加：

```python
# ── Workspace File Tools ──

import fnmatch
from pathlib import Path
from app.core.workspace_files import WorkspaceFileManager


@tool
def list_workspace_files(
    workspace_id: str,
    pattern: str = "*",
    max_results: int = 50,
) -> str:
    """列出工作区中的文件清单。使用 glob 模式过滤。
    用此工具查看工作区有哪些文件可用。

    Args:
        workspace_id: 工作区 ID
        pattern: 文件名匹配模式，如 "*.md"、"docs/**"、"*需求*"
        max_results: 最多返回数（默认 50，最大 200）

    Returns:
        文件列表文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        files = fm.list_files(pattern, min(max_results, 200))
        if not files:
            return "工作区暂无文件。"
        lines = [f"共 {len(files)} 个文件：", ""]
        for f in files:
            summary = f.get("summary", "")
            summary_fragment = f" — {summary[:60]}" if summary else ""
            lines.append(
                f"- {f['path']} ({f.get('type', '?')}, "
                f"{_fmt_size(f.get('size', 0))})"
                f"{summary_fragment}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_workspace_files error: {e}")
        return f"无法列出工作区文件：{e}"


@tool
def read_workspace_file(
    workspace_id: str,
    file_path: str,
    max_chars: int = 8000,
) -> str:
    """读取工作区中指定文件的内容。
    用此工具获取文件全文来分析。
    .md 文件返回 Markdown 原文，Office 文档返回转换后的文本内容。

    Args:
        workspace_id: 工作区 ID
        file_path: 文件相对路径（从 list_workspace_files 获取）
        max_chars: 最大读取字符数（默认 8000，最大 100000）

    Returns:
        文件内容文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        result = fm.read_file(file_path, min(max_chars, 100000))
        header = f"--- {result['path']} ({_fmt_size(result['size'])}) ---\n"
        if result["truncated"]:
            header += f"[文件过长，仅显示前 {max_chars} 字符]\n"
        return header + result["text"]
    except FileNotFoundError as e:
        return f"文件不存在：{e}"
    except RuntimeError as e:
        return f"无法解析文件：{e}"
    except Exception as e:
        logger.error(f"read_workspace_file error: {e}")
        return f"读取文件失败：{e}"


@tool
def read_file_section(
    workspace_id: str,
    file_path: str,
    start_line: int = 1,
    end_line: int = 100,
) -> str:
    """读取大文件的指定行范围。对超大文件分段分析很有用。
    先看文件总行数再分段读取。

    Args:
        workspace_id: 工作区 ID
        file_path: 文件相对路径
        start_line: 起始行号（从 1 开始）
        end_line: 结束行号

    Returns:
        指定行范围内的文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        result = fm.read_file_section(file_path, start_line, end_line)
        lines_text = "\n".join(str(l) for l in result["lines"])
        return (
            f"--- {result['path']} 第 {result['start_line']}-{result['end_line']} 行 "
            f"(共 {result['total_lines']} 行) ---\n{lines_text}"
        )
    except FileNotFoundError as e:
        return f"文件不存在：{e}"
    except Exception as e:
        return f"读取文件失败：{e}"


@tool
def search_in_workspace(
    workspace_id: str,
    query: str,
    file_pattern: str = "*.md",
    max_results: int = 10,
) -> str:
    """在工作区文件中搜索关键词或短语。
    对 .md 和 .txt 文件做全文搜索。返回匹配文件及上下文片段。

    Args:
        workspace_id: 工作区 ID
        query: 搜索关键词
        file_pattern: 限定文件类型，默认 "*.md"
        max_results: 最多返回结果数（默认 10，最大 50）

    Returns:
        搜索结果文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        results = fm.search_files(query, file_pattern, min(max_results, 50))
        if not results:
            return f"在工作区文件中未找到包含「{query}」的内容。"
        lines = [f"搜索「{query}」共找到 {sum(r['match_count'] for r in results)} 处匹配：", ""]
        for r in results:
            lines.append(f"📄 {r['path']} ({r['match_count']} 处匹配):")
            for m in r["matches"][:5]:
                context = m["text"][:120]
                lines.append(f"  第 {m['line']} 行: {context}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"搜索失败：{e}"


@tool
def write_workspace_file(
    workspace_id: str,
    file_path: str,
    content: str,
) -> str:
    """在工作区中创建或更新文件。
    用于 AI 生成的产出——分析报告、需求总结、会议纪要等。
    文件会自动写入工作区的 _generated/ 子目录。

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
        return f"文件已写入工作区：{result['path']} ({_fmt_size(result['size'])})"
    except Exception as e:
        return f"写入文件失败：{e}"


@tool
def get_workspace_info(workspace_id: str) -> str:
    """获取当前工作区的整体概况。
    返回项目名称、描述、文件总数及类型分布、所有文件清单。

    Args:
        workspace_id: 工作区 ID

    Returns:
        工作区概览文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        info = fm.get_info()
        lines = [
            f"📁 工作区文件概况",
            f"   文件总数: {info['file_count']}",
        ]
        if info["by_type"]:
            type_str = ", ".join(f"{k}: {v}个" for k, v in info["by_type"].items())
            lines.append(f"   类型分布: {type_str}")
        if info["by_source"]:
            src_str = ", ".join(f"{k}: {v}个" for k, v in info["by_source"].items())
            lines.append(f"   来源分布: {src_str}")
        lines.append("")
        if info["files"]:
            lines.append("文件清单：")
            for f in info["files"]:
                summary = f.get("summary", "")
                s = f" - {f['path']} ({f.get('type', '?')})"
                if summary:
                    s += f" — {summary[:80]}"
                lines.append(s)
        else:
            lines.append("（暂无文件）")
        return "\n".join(lines)
    except Exception as e:
        return f"获取工作区信息失败：{e}"


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    return f"{size / 1024 / 1024:.1f}MB"
```

在 `app/agent/pm/phase1/mining_agent.py` 中注册新工具（MiningAgent.__init__ 的 pm_tools 列表末尾）：

```python
# 在现有 import 后面追加
from app.agent.pm.tools import (
    get_profile_summary,
    reset_current_thread_id,
    set_current_thread_id,
    set_pending_questions,
    update_requirement_profile,
    # 新增文件工具
    list_workspace_files,
    read_workspace_file,
    read_file_section,
    search_in_workspace,
    write_workspace_file,
    get_workspace_info,
)

# 在 __init__ 的 pm_tools 列表末尾追加
self.pm_tools = [
    # ... 原有工具不变 ...
    # 新增文件工具
    list_workspace_files,
    read_workspace_file,
    read_file_section,
    search_in_workspace,
    write_workspace_file,
    get_workspace_info,
]
```

- [ ] **Step 1: tools.py 添加 6 个文件工具**

Edit `app/agent/pm/tools.py` — 在文件末尾添加上述所有代码（包含 `_fmt_size` 工具函数和 6 个 `@tool` 函数）。

- [ ] **Step 2: mining_agent.py 注册工具**

Edit `app/agent/pm/phase1/mining_agent.py` — 更新 import 和 pm_tools 列表。

- [ ] **Step 3: 验证 Agent 可加载**

Run: `cd /home/startower/pm-agent-dev && python3 -c "from app.agent.pm.phase1.mining_agent import MiningAgent; a = MiningAgent(); print([t.name for t in a.pm_tools]); print('OK')"`
Expected: 列表应包含 6 个新工具名

- [ ] **Step 4: Commit**

```bash
git add app/agent/pm/tools.py app/agent/pm/phase1/mining_agent.py
git commit -m "feat: add 6 workspace file tools to MiningAgent"
```

---

### Task 4: 上下文注入 — PMAgentService 自动感知工作区文件

**Files:**
- Modify: `app/services/pm_agent_service.py`

在 `PMAgentService.chat()` 方法中，当 `workspace_id` 非空且工作区有文件时，通过 `chat_with_context` 注入轻量上下文。

关键改动位置（`pm_agent_service.py` 中 `chat` 方法，约第 82 行开始）：

```python
# 在 chat() 方法中，调用 get_mining_agent().chat() 之前
# 构建工作区文件上下文
workspace_context = None
if workspace_id:
    try:
        ws = await self._ds.get_workspace(workspace_id)
        files = await self._ds.list_workspace_files(workspace_id, max_results=30)
        if ws and files:
            file_summary_lines = [
                f"- {f['path']} ({f.get('type', '?')})" for f in files
            ]
            workspace_context = (
                f"当前工作区「{ws.get('name', '')}」包含以下文件：\n"
                + "\n".join(file_summary_lines)
                + "\n\n用户可能会要求你分析这些文件。使用 list_workspace_files / "
                  "read_workspace_file 等文件工具查阅和分析。"
            )
    except Exception:
        logger.debug(f"[{thread_id}] Failed to build workspace context")
```

然后将此 `workspace_context` 作为 `context_messages` 注入到 `get_mining_agent().chat()` 调用中：

当前代码：
```python
async for event in get_mining_agent().chat(
    message,
    thread_id,
    force_knowledge=use_knowledge,
):
```

改为：
```python
context_msgs = []
if workspace_context:
    context_msgs.append({"role": "system", "content": workspace_context})

if context_msgs:
    # 使用 chat_with_context 注入上下文
    async for event in get_mining_agent().chat_with_context(
        message=message,
        thread_id=thread_id,
        force_knowledge=use_knowledge,
        context_messages=context_msgs,
    ):
        if event.get("type") == "content" and isinstance(event.get("data"), str):
            assistant_content += event["data"]
        yield event
else:
    async for event in get_mining_agent().chat(
        message,
        thread_id,
        force_knowledge=use_knowledge,
    ):
        if event.get("type") == "content" and isinstance(event.get("data"), str):
            assistant_content += event["data"]
        yield event
```

注意：`chat()` 和 `chat_with_context()` 的区别在于：
- `chat()` 是简单封装，内部调用 `chat_with_context()`
- `chat_with_context()` 直接暴露 `context_messages` 参数
- 所以可以直接统一调用 `chat_with_context()`，只是传不同的参数

简化写法——统一使用 `chat_with_context`：

```python
async for event in get_mining_agent().chat_with_context(
    message=message,
    thread_id=thread_id,
    force_knowledge=use_knowledge,
    context_messages=context_msgs if context_msgs else None,
):
```

- [ ] **Step 1: 修改 PMAgentService.chat()**

Edit `app/services/pm_agent_service.py` — 在 `chat` 方法中构建 workspace_context 并注入。

- [ ] **Step 2: 验证语法**

Run: `cd /home/startower/pm-agent-dev && python3 -c "import ast; ast.parse(open('app/services/pm_agent_service.py').read()); print('Syntax OK')"`

- [ ] **Step 3: Commit**

```bash
git add app/services/pm_agent_service.py
git commit -m "feat: inject workspace file context into agent chat"
```

---

### Task 5: 前端 — WorkspaceDetail 文件 Tab

**Files:**
- Create: `reqcollect-web/src/components/workspace/FileManager.vue`
- Create: `reqcollect-web/src/api/workspace_files.ts`
- Modify: `reqcollect-web/src/views/WorkspaceDetail.vue`

**reqcollect-web/src/api/workspace_files.ts**:

```typescript
/* ── Workspace Files API ── */

import { apiGet, apiPost, apiDelete } from './client'

export interface WorkspaceFile {
  path: string
  size: number
  type: string
  source: string
  uploaded_at: string
  summary: string
}

export async function fetchWorkspaceFiles(
  wsId: string,
  pattern?: string
): Promise<WorkspaceFile[]> {
  const params = pattern ? `?pattern=${encodeURIComponent(pattern)}` : ''
  const res: any = await apiGet(`/workspaces/${wsId}/files${params}`)
  return res.files
}

export async function uploadWorkspaceFile(
  wsId: string,
  file: File,
  token: string
): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await fetch(`/api/workspaces/${wsId}/files/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || 'Upload failed')
  }
  return resp.json()
}

export async function readWorkspaceFile(
  wsId: string,
  path: string,
  maxChars?: number
): Promise<any> {
  const params = maxChars ? `?max_chars=${maxChars}` : ''
  const res: any = await apiGet(
    `/workspaces/${wsId}/files/${encodeURIComponent(path)}${params}`
  )
  return res.file
}

export async function deleteWorkspaceFile(
  wsId: string,
  path: string
): Promise<void> {
  await apiDelete(`/workspaces/${wsId}/files/${encodeURIComponent(path)}`)
}

export async function fetchWorkspaceFilesInfo(wsId: string): Promise<any> {
  const res: any = await apiGet(`/workspaces/${wsId}/files/info`)
  return res.info
}
```

**reqcollect-web/src/components/workspace/FileManager.vue** — 文件管理组件：

```vue
<template>
  <div class="file-manager">
    <!-- Top bar -->
    <div class="fm-toolbar">
      <div class="fm-toolbar-left">
        <span class="fm-count" v-if="files.length">共 {{ files.length }} 个文件</span>
        <span class="fm-count" v-else>暂无文件</span>
      </div>
      <div class="fm-toolbar-actions">
        <el-upload
          :action="uploadUrl"
          :headers="uploadHeaders"
          :show-file-list="false"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :before-upload="beforeUpload"
          :disabled="uploading"
          accept=".md,.txt,.json,.yaml,.yml,.docx,.xlsx"
        >
          <el-button size="small" type="primary" :loading="uploading">
            {{ uploading ? '上传中...' : '+ 上传文件' }}
          </el-button>
        </el-upload>
      </div>
    </div>

    <!-- Upload progress -->
    <div v-if="uploadMsg" :class="['upload-msg', uploadMsgType]">
      {{ uploadMsg }}
    </div>

    <!-- Empty state -->
    <div v-if="!loading && files.length === 0" class="fm-empty">
      <div class="fm-empty-icon">📁</div>
      <p>暂无文件，请上传 Markdown、Office 文档</p>
      <p class="fm-empty-hint">支持 .md .txt .docx .xlsx 等格式</p>
    </div>

    <!-- File table -->
    <el-table
      v-else
      :data="files"
      v-loading="loading"
      stripe
      style="width:100%"
      size="small"
      empty-text="暂无文件"
    >
      <el-table-column label="文件名" min-width="240">
        <template #default="{ row }">
          <div class="fm-file-cell">
            <span class="fm-file-icon">{{ fileIcon(row.type) }}</span>
            <span class="fm-file-name">{{ row.path }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="70">
        <template #default="{ row }">
          <el-tag size="small">{{ row.type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="80">
        <template #default="{ row }">{{ fmtSize(row.size) }}</template>
      </el-table-column>
      <el-table-column label="来源" width="80">
        <template #default="{ row }">
          <el-tag :type="sourceTagType(row.source)" size="small">{{ sourceLabel(row.source) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上传时间" width="170">
        <template #default="{ row }">{{ fmtDate(row.uploaded_at) }}</template>
      </el-table-column>
      <el-table-column label="摘要" min-width="200">
        <template #default="{ row }">
          <span class="fm-summary">{{ row.summary || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="previewFile(row)">预览</el-button>
          <el-button text size="small" type="primary" @click="analyzeFile(row)">分析</el-button>
          <el-popconfirm title="确定删除此文件？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button text size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Preview dialog -->
    <el-dialog v-model="previewVisible" :title="previewFileTitle" width="800px" top="5vh">
      <div v-if="previewLoading" v-loading="true" style="height:300px" />
      <div v-else class="fm-preview">
        <div class="fm-preview-meta">
          <span>大小: {{ fmtSize(previewContent?.size || 0) }}</span>
          <span v-if="previewContent?.truncated" class="fm-truncated-warn">
            ⚠ 文件过长，仅显示前 {{ previewMaxChars }} 字符
          </span>
        </div>
        <div v-if="previewContent?.type === 'md'" class="fm-preview-md" v-html="renderedMarkdown" />
        <pre v-else class="fm-preview-text">{{ previewContent?.text || '' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { fetchWorkspaceFiles, uploadWorkspaceFile, readWorkspaceFile, deleteWorkspaceFile } from '@/api/workspace_files'
import type { WorkspaceFile } from '@/api/workspace_files'

const props = defineProps<{ workspaceId: string }>()

const files = ref<WorkspaceFile[]>([])
const loading = ref(false)
const uploading = ref(false)
const uploadMsg = ref('')
const uploadMsgType = ref('info')

const previewVisible = ref(false)
const previewLoading = ref(false)
const previewFileTitle = ref('')
const previewContent = ref<any>(null)
const previewMaxChars = 8000

const token = computed(() => localStorage.getItem('reqcollect_token') || '')
const uploadUrl = computed(() => `/api/workspaces/${props.workspaceId}/files/upload`)
const uploadHeaders = computed(() => ({ Authorization: `Bearer ${token.value}` }))

const renderedMarkdown = computed(() => {
  if (!previewContent.value?.text) return ''
  return marked.parse(previewContent.value.text) as string
})

onMounted(loadFiles)

async function loadFiles() {
  loading.value = true
  try {
    files.value = await fetchWorkspaceFiles(props.workspaceId)
  } catch (e: any) {
    ElMessage.error('加载文件列表失败')
  } finally {
    loading.value = false
  }
}

function beforeUpload(file: File) {
  const allowed = ['.md', '.txt', '.json', '.yaml', '.yml', '.docx', '.xlsx']
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的文件类型 ${ext}`)
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件超过 10MB 限制')
    return false
  }
  uploading.value = true
  uploadMsg.value = ''
  return true
}

function onUploadSuccess(res: any) {
  uploading.value = false
  if (res?.success) {
    ElMessage.success('文件上传成功')
    loadFiles()
  } else {
    ElMessage.error(res?.detail || '上传失败')
  }
}

function onUploadError(err: any) {
  uploading.value = false
  ElMessage.error(err?.message || '上传失败')
}

async function handleDelete(row: WorkspaceFile) {
  try {
    await deleteWorkspaceFile(props.workspaceId, row.path)
    ElMessage.success('已删除')
    loadFiles()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function previewFile(row: WorkspaceFile) {
  previewVisible.value = true
  previewLoading.value = true
  previewFileTitle.value = row.path
  previewContent.value = null
  try {
    previewContent.value = await readWorkspaceFile(
      props.workspaceId, row.path, previewMaxChars
    )
  } catch (e: any) {
    ElMessage.error('读取文件失败')
  } finally {
    previewLoading.value = false
  }
}

function analyzeFile(row: WorkspaceFile) {
  // Emit to parent to navigate to chat with context
  ElMessage.info(`分析功能即将实现：将「${row.path}」注入对话上下文`)
}

function fileIcon(type: string): string {
  const icons: Record<string, string> = {
    md: '📝', txt: '📄', json: '📋', yaml: '⚙️', yml: '⚙️',
    docx: '📘', xlsx: '📊',
  }
  return icons[type] || '📄'
}

function fmtSize(size: number): string {
  if (size < 1024) return `${size}B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}KB`
  return `${(size / 1024 / 1024).toFixed(1)}MB`
}

function sourceTagType(source: string) {
  return { upload: '', generated: 'success', linked: 'info' }[source] || 'info'
}

function sourceLabel(source: string) {
  return { upload: '上传', generated: 'AI生成', linked: '同步' }[source] || source
}

function fmtDate(d: string) {
  if (!d) return ''
  try { return new Date(d).toLocaleString('zh-CN') } catch { return '' }
}
</script>

<style scoped>
.file-manager { padding: 0; }
.fm-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; gap: 12px; }
.fm-toolbar-left { display: flex; align-items: center; gap: 8px; }
.fm-count { font-size: 13px; color: #86909c; }
.fm-file-cell { display: flex; align-items: center; gap: 6px; }
.fm-file-icon { font-size: 18px; }
.fm-file-name { font-size: 14px; }
.fm-summary { font-size: 12px; color: #86909c; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-block; }
.upload-msg { padding: 8px 12px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; }
.upload-msg.info { background: #e8f4ff; color: #1d7cf0; }
.upload-msg.error { background: #ffe8e8; color: #f53f3f; }
.fm-empty { text-align: center; padding: 60px 20px; color: #86909c; }
.fm-empty-icon { font-size: 48px; margin-bottom: 12px; }
.fm-empty-hint { font-size: 12px; color: #c9cdd4; }
.fm-preview-meta { margin-bottom: 12px; font-size: 12px; color: #86909c; display: flex; gap: 16px; }
.fm-truncated-warn { color: #fa8c16; }
.fm-preview-md { padding: 16px; background: #f7f8fa; border-radius: 4px; max-height: 70vh; overflow-y: auto; }
.fm-preview-text { padding: 16px; background: #f7f8fa; border-radius: 4px; max-height: 70vh; overflow-y: auto; white-space: pre-wrap; font-size: 13px; }
</style>
```

**WorkspaceDetail.vue** — 在 Tabs 中插入文件 Tab：

```vue
<!-- 在需求图谱 Tab 之前插入 -->
<el-tab-pane label="📁 文件" name="files">
  <div v-if="!workspace" v-loading="true" style="height:200px" />
  <FileManager v-else :workspace-id="route.params.id as string" />
</el-tab-pane>
```

并在 `<script>` 中添加 import：

```typescript
import FileManager from '@/components/workspace/FileManager.vue'
```

- [ ] **Step 1: 创建 API 文件**

Write `reqcollect-web/src/api/workspace_files.ts`.

- [ ] **Step 2: 创建 FileManager 组件**

Write `reqcollect-web/src/components/workspace/FileManager.vue`.

- [ ] **Step 3: 修改 WorkspaceDetail.vue**

Edit `reqcollect-web/src/views/WorkspaceDetail.vue` — 插入 `FileManager` 组件和 Tab。

- [ ] **Step 4: 验证前端构建**

Run: `cd /home/startower/pm-agent-dev/reqcollect-web && npx vue-tsc --noEmit 2>&1 | head -30 || true`
Expected: 没有类型错误（或仅有现有警告）

- [ ] **Step 5: Commit**

```bash
git add reqcollect-web/src/api/workspace_files.ts reqcollect-web/src/components/workspace/FileManager.vue reqcollect-web/src/views/WorkspaceDetail.vue
git commit -m "feat: add workspace file manager UI with upload, preview, delete"
```

---

### Task 6: 编写测试 + Evaluate

**Files:**
- Create: `tests/test_workspace_files.py`

**tests/test_workspace_files.py**:

```python
"""Tests for WorkspaceFileManager and workspace file tools."""

import json
import tempfile
from pathlib import Path

import pytest

from app.core.file_handler import FileValidationError
from app.core.workspace_files import WorkspaceFileManager


@pytest.fixture
def tmp_ws_id() -> str:
    return "test-ws-001"


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point config.data_dir to a temp dir."""
    monkeypatch.setattr("app.config.config.data_dir", str(tmp_path))
    return tmp_path


class TestWorkspaceFileManager:
    def test_list_empty(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        assert fm.list_files() == []

    def test_upload_and_list(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        result = fm.upload_file("test.md", b"# Hello\nThis is a test.", "user1")
        assert result["path"] == "test.md"
        assert result["type"] == "md"

        files = fm.list_files()
        assert len(files) == 1
        assert files[0]["path"] == "test.md"
        assert files[0]["source"] == "upload"

    def test_upload_and_read(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("readme.md", b"# Readme\nContent here.", "user1")
        content = fm.read_file("readme.md")
        assert "Readme" in content["text"]
        assert content["type"] == "md"
        assert not content["truncated"]

    def test_read_truncated(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        long_text = "x" * 10000
        fm.upload_file("long.txt", long_text.encode(), "user1")
        content = fm.read_file("long.txt", max_chars=100)
        assert content["truncated"]
        assert len(content["text"]) == 100

    def test_read_file_section(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        lines = "\n".join(f"line {i}" for i in range(1, 101))
        fm.upload_file("lines.txt", lines.encode(), "user1")
        result = fm.read_file_section("lines.txt", 10, 20)
        assert result["start_line"] == 10
        assert result["end_line"] == 20
        assert len(result["lines"]) == 10
        assert "line 10" in result["lines"][0]

    def test_search(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("a.md", b"# Project Alpha\nRequirement: login", "user1")
        fm.upload_file("b.md", b"# Project Beta\nRequirement: export", "user1")

        results = fm.search_files("login")
        assert len(results) == 1
        assert results[0]["path"] == "a.md"

    def test_search_across_files(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("a.md", b"Alpha content", "user1")
        fm.upload_file("b.md", b"Beta also has content", "user1")

        results = fm.search_files("content")
        assert len(results) >= 1

    def test_search_respects_pattern(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("a.md", b"keyword in md", "user1")
        fm.upload_file("b.txt", b"keyword in txt", "user1")

        results = fm.search_files("keyword", file_pattern="*.md")
        assert len(results) == 1
        assert results[0]["path"] == "a.md"

    def test_write_file(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        result = fm.write_file("report.md", "# Analysis Report\n\nDone.")
        assert result["path"] == "report.md"

        content = fm.read_file("report.md")
        assert "Analysis Report" in content["text"]

    def test_write_updates_index(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.write_file("output.md", "# Output")
        info = fm.get_info()
        assert info["file_count"] == 1
        assert info["by_source"].get("generated", 0) == 1

    def test_delete_file(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("todelete.md", b"Delete me", "user1")
        assert len(fm.list_files()) == 1
        fm.delete_file("todelete.md")
        assert len(fm.list_files()) == 0

    def test_delete_nonexistent(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        assert not fm.delete_file("nonexistent.md")

    def test_get_file_info(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("info.md", b"# Info", "user1")
        info = fm.get_file_info("info.md")
        assert info is not None
        assert info["path"] == "info.md"

    def test_get_file_info_missing(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        assert fm.get_file_info("missing.md") is None

    def test_get_info_empty(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        info = fm.get_info()
        assert info["file_count"] == 0
        assert info["by_type"] == {}
        assert info["by_source"] == {}

    def test_get_info_with_files(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("a.md", b"a", "user1")
        fm.upload_file("b.md", b"b", "user1")
        fm.write_file("c.md", "c")
        info = fm.get_info()
        assert info["file_count"] == 3
        assert info["by_type"].get("md", 0) == 3

    def test_upload_invalid_type(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        with pytest.raises(FileValidationError):
            fm.upload_file("bad.exe", b"nope", "user1")

    def test_read_nonexistent(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        with pytest.raises(FileNotFoundError):
            fm.read_file("nope.md")

    def test_filter_by_pattern(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("readme.md", b"# R", "user1")
        fm.upload_file("notes.txt", b"notes", "user1")
        fm.upload_file("data.json", b"{}", "user1")

        mds = fm.list_files(pattern="*.md")
        assert len(mds) == 1
        assert mds[0]["type"] == "md"

    def test_list_respects_max_results(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        for i in range(5):
            fm.upload_file(f"f{i}.md", f"file {i}".encode(), "user1")
        assert len(fm.list_files(max_results=2)) == 2

    def test_upload_deduplicate(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("same.md", b"same content", "user1")
        fm.upload_file("same.md", b"same content", "user1")
        assert len(fm.list_files()) == 1

    def test_path_traversal_rejected(self):
        # _validate_file_path is a module-level function
        from app.core.workspace_files import _validate_file_path
        from app.core.file_handler import FileValidationError
        with pytest.raises(FileValidationError):
            _validate_file_path(Path("/tmp"), "../../etc/passwd")
```

- [ ] **Step 1: 运行测试**

Run: `cd /home/startower/pm-agent-dev && python3 -m pytest tests/test_workspace_files.py -v 2>&1`
Expected: 全部 PASS

- [ ] **Step 2: 运行回归测试**

Run: `cd /home/startower/pm-agent-dev && python3 -m pytest tests/ -v 2>&1`
Expected: 新增测试全部通过，原有测试不受影响

- [ ] **Step 3: 检测改动影响**

Run: `cd /home/startower/pm-agent-dev && npx gitnexus detect-changes` (如果可用)
Expected: 仅影响新增模块，不破坏现有符号

- [ ] **Step 4: Evaluate 报告**

Write Evaluate 报告 `.execution/workspace-file-system/report.md`：
- 逐条验证验收标准（见 spec 第 10 节）
- 记录测试结果
- 回归检查

- [ ] **Step 5: 最终提交**

```bash
git add tests/test_workspace_files.py .execution/workspace-file-system/
git commit -m "feat: add unit tests for WorkspaceFileManager"
```
