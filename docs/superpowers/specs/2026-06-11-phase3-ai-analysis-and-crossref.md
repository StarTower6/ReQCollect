# Phase 3: AI 主动分析 + 文件交叉引用图

> **设计规范**

**目标**: 赋予 Agent 后台静默分析工作区文件的能力，并将工作区文件纳入 Wiki 引用图谱。

**总改动文件**:
- 新增: `app/core/workspace_analyzer.py`
- 修改: `app/core/workspace_files.py`, `app/db/models.py`, `app/db/__init__.py`, `app/db/compat.py`, `app/db/repository.py`, `app/api/wiki.py`, `app/agent/pm/tools.py`, `app/agent/pm/phase1/mining_agent.py`, `app/services/pm_agent_service.py`
- 修改前端: `GraphView.vue`, `FileTreePanel.vue`

---

## 模块 1: Agent 主动感知（后台静默分析）

### 1.1 `app/core/workspace_analyzer.py`（新文件）

```python
"""后台文件分析器 — 调用 LLM 提取文件摘要、标签、需求领域。

与 WorkspaceFileManager 配合，在文件上传/写入/同步后异步触发。
分析结果写入文件索引的 analysis 字段。失败时静默降级。
"""

import json, re
from pathlib import Path
from app.core.workspace_files import WorkspaceFileManager
from app.core.llm_factory import llm_factory
from app.config import config

_analysis_cache: dict[str, dict] = {}

def _parse_llm_json(raw: str) -> dict | None:
    """从 LLM 回复中提取 JSON 对象，容忍 markdown 代码块包裹。"""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None

async def analyze_workspace_file(workspace_id: str, file_path: str) -> dict:
    """分析单个文件，写入索引，返回分析结果。
    
    已有 analysis 则跳过（幂等）。
    失败时静默降级，不抛异常。
    """
    fm = WorkspaceFileManager(workspace_id)
    info = fm.get_file_info(file_path)
    if info and info.get("analysis"):
        return info["analysis"]
    
    try:
        content = fm.read_file(file_path, max_chars=4000)
    except Exception:
        fm.upsert_analysis(file_path, {"summary": "", "tags": [], "domain": ""})
        return {"summary": "", "tags": [], "domain": ""}
    
    text = content.get("text", "")
    if not text.strip():
        fm.upsert_analysis(file_path, {"summary": "", "tags": [], "domain": ""})
        return {"summary": "", "tags": [], "domain": ""}
    
    prompt = (
        "Analyze the following file content. Return ONLY a JSON object:\n"
        '{"summary": "one-sentence summary in Chinese within 30 chars", '
        '"tags": ["tag1", "tag2", "tag3"], '
        '"domain": "related requirement domain in Chinese"}\n\n'
        f"File: {file_path}\n\nContent:\n{text[:3000]}"
    )
    
    try:
        model = llm_factory.create_chat_model(
            model=config.llm_model, temperature=0.1, streaming=False
        )
        response = await model.ainvoke(prompt)
        result_text = response.content if hasattr(response, 'content') else str(response)
        result = _parse_llm_json(result_text) or {"summary": "", "tags": [], "domain": ""}
    except Exception:
        result = {"summary": "", "tags": [], "domain": ""}
    
    fm.upsert_analysis(file_path, result)
    return result
```

### 1.2 触发点

在 `pm_agent_service.py` 的 `chat()` 方法中，文件上下文构建后加入分析信息：

```python
# Inject analysis results into workspace context
if workspace_id:
    # ... existing workspace context ...
    for f in files:
        if f.get("analysis") and f["analysis"].get("tags"):
            tags = ",".join(f["analysis"]["tags"])
            file_summary_lines.append(f"  [{tags}]")
```

在 API 层触发分析：

```python
# app/api/workspace.py — ws_files_upload after success
asyncio.ensure_future(analyze_workspace_file(workspace_id, safe_name))
```

### 1.3 `WorkspaceFileManager` 新增

```python
def upsert_analysis(self, relative_path: str, analysis: dict) -> None:
    """写入 analysis 到文件索引，不修改其他字段。"""
    index = _load_index(self._files_dir)
    for f in index:
        if f["path"] == relative_path:
            f["analysis"] = analysis
            break
    _save_index(self._files_dir, index)
```

### 1.4 前端展示

`FileTreePanel.vue` 中扩展：

- 文件行在有 `analysis.tags` 时显示标签药丸（灰色小标签）
- 鼠标悬浮 tooltip 显示摘要
- 复用现有的 `.ftp-ai` 样式类

---

## 模块 2: 文件交叉引用图

### 2.1 数据模型扩展

`app/db/models.py` — WikiLink 表重构：

```python
class WikiLink(Base):
    __tablename__ = "wiki_links"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_ref: Mapped[str] = mapped_column(String(128), index=True)
    source_type: Mapped[str] = mapped_column(String(16), default="wiki")  # "wiki" | "file"
    target_ref: Mapped[str] = mapped_column(String(128), index=True)
    target_type: Mapped[str] = mapped_column(String(16), default="wiki")  # "wiki" | "file"
    link_type: Mapped[str] = mapped_column(String(32), default="reference")
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="")
```

**SQLite/JSON 兼容**: `compat.py` 中对应改存储格式。

**迁移兼容**: 上线后旧数据自动适配 `source_ref=source_page_id, source_type="wiki"`。

### 2.2 DataStore 协议扩展

`app/db/__init__.py`:

```python
@abstractmethod
async def save_file_links(
    self, workspace_id: str,
    source_ref: str, source_type: str,
    targets: list[tuple[str, str]],  # [(target_ref, target_type), ...]
) -> None: ...

@abstractmethod
async def get_file_links(self, workspace_id: str, ref: str, ref_type: str) -> dict:
    """返回 {outgoing: [...], incoming: [...]}"""
```

### 2.3 `[[链接]]` 解析逻辑扩展

`app/api/wiki.py` 中的 `WIKILINK_RE` 解析逻辑：

```
链接目标文本 → 先查 Wiki 页面标题
  → 匹配成功 → source_type="wiki", target_type="wiki"
  → 匹配失败 → 查工作区文件名（list_workspace_files）
    → 匹配成功 → source_type="wiki", target_type="file"
    → 匹配失败 → 丢弃（不报错）
```

工作区文件内容中的 `[[链接]]` 解析（由 `write_workspace_file` 触发）：

```
文件内容写入后 → 扫描 [[链接]] → 同上解析逻辑
  → source_ref=file_path, source_type="file"
  → 存入 save_file_links
```

### 2.4 图谱 API 扩展

`GET /api/wiki/graph/{workspace_id}`:

```python
@router.get("/wiki/graph/{workspace_id}")
async def wiki_graph(workspace_id: str, ...):
    # 原有的 wiki 节点
    wiki_nodes: query wiki pages in workspace
    # 新增：从 wiki_links 中收集 file 节点
    file_refs: set of (target_ref, source_ref) where target_type="file" or source_type="file"
    file_nodes: [{"id": f"file:{ref}", "label": ref.split("/")[-1], "type": "file", "value": 1}]
    # WikiLink 已有的 edges 包含 file 引用
    edges: [{"from": f"{src_type}:{src_ref}", "to": f"{tgt_type}:{tgt_ref}", ...}]
    return {"nodes": wiki_nodes + file_nodes, "edges": edges}
```

### 2.5 GraphView.vue 扩展

```typescript
// 节点颜色:
const nodeColor = (type: string) => type === 'file' ? '#67c23a' : '#409eff'

// 节点点击:
if (node.type === 'file') {
  // 跳转到工作区文件预览（使用 router 或 emit 事件）
  router.push(`/workspace/${workspaceId}/files/${node.label}`)
}
// wiki 节点保持原有行为
```

### 2.6 Agent write 时自动建链

`app/agent/pm/tools.py` — `write_workspace_file` 增强：

```python
@tool
def write_workspace_file(workspace_id, file_path, content):
    fm = WorkspaceFileManager(workspace_id)
    result = fm.write_file(file_path, content)
    # 解析 [[链接]]
    from app.api.wiki import WIKILINK_RE
    links = WIKILINK_RE.findall(content)
    if links and has_datastore:
        targets = []
        for title, _ in links:
            # 查 wiki 页面
            page = ds.resolve_wiki_title(workspace_id, title)
            if page:
                targets.append((page["id"], "wiki"))
            # 查工作区文件
            elif any(f["path"] == title for f in fm.list_files()):
                targets.append((title, "file"))
        if targets:
            ds.save_file_links(workspace_id, file_path, "file", targets)
    return f"文件已写入：{result['path']}"
```

---

## 范围边界（明确不做）

| 包含 | 不包含 |
|---|---|
| 文件自动分析（摘要 + 标签） | 语义/向量搜索 |
| 文件参与 Wiki 图谱可视化 | 图谱布局自动排列 |
| `[[file.md]]` 跨文件引用 | 图谱节点拖拽编辑 |
| Agent 写入时自动建链 | 图谱节点删除操作 |
| 文件摘要展示在文件树 | 基于图谱的推荐算法 |
| GraphView 显示文件节点 | 文件关联度打分 |

---

## 索引层改动说明

`WorkspaceFileManager._index.json` 新增字段：

```json
{
  "path": "需求文档.md",
  "type": "md",
  "size": 1234,
  "source": "upload",
  "uploaded_at": "...",
  "analysis": {
    "summary": "报销审批系统需求",
    "tags": ["报销", "审批流", "财务"],
    "domain": "审批流系统"
  }
}
```

`WikiLink` JSON 存储格式：

```json
{
  "id": 1,
  "source_ref": "需求文档.md",
  "source_type": "file",
  "target_ref": "page_abc123",
  "target_type": "wiki",
  "link_type": "reference",
  "workspace_id": "ws_xxx"
}
```
