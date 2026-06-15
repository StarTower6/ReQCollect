# Spec: 工作区文件系统 — 让 Agent 感知并分析项目文件

> 日期: 2026-06-10
> 状态: 定稿 ✓
> 关联: [[pge-mandatory-for-all-work]]

## 1. 概述

### 问题

ReQCollect 的 Agent 当前只能操作需求画像字段，无法感知工作区中的文件。
用户希望 Agent 能像 Claude Code 一样读取、搜索、分析项目文件，实现
"Obsidian + Claude Code" 模式——在一个工作区中管理需求文档和相关资料，
Agent 能自主查阅并基于文件内容做分析。

### 核心目标

让 ReQCollect 的 MiningAgent 能够:
1. 列出工作区中的文件
2. 读取文件内容（.md 全文，Office 文档转换后文本）
3. 在工作区文件中搜索关键词/内容
4. 在工作区写入 AI 产出（分析报告、需求记录等）
5. 在对话中自动感知工作区文件上下文

### 不做什么

- ❌ 不实现实时同步（inotify 等 Watch 机制放到 Phase 3）
- ❌ 不实现文件间交叉引用图谱（Phase 3）
- ❌ 不改变现有 /api/pm/\* 路径结构
- ❌ 不把前端转 React/Vue

## 2. 数据模型

### Workspace 扩展字段

```python
# 在现有 workspace 数据模型基础上增加
{
  # ... 已有字段 (id, name, code, description, created_by, is_active)
  
  # 新增
  "path": "",              # 关联的服务器目录路径（可选）
  "file_count": 0,         # 缓存文件数
  "generated_dir": "_generated",  # AI 产出子目录名
  "last_synced_at": "",    # 上次文件同步时间
}
```

### WorkspaceFile 索引

位置: `<workspace_data_dir>/files/_index.json`

```json
[
  {
    "path": "需求文档-v2.md",
    "size": 12580,
    "type": "md",
    "source": "upload",
    "uploaded_at": "2026-06-10T10:00:00Z",
    "uploaded_by": "user_1",
    "summary": "ERP 系统采购模块需求初稿"
  }
]
```

`source` 取值: `"upload"`（用户上传）、`"linked"`（服务器目录同步）、`"generated"`（AI 产出）

### 文件存储目录结构

```
<data_dir>/workspaces/<ws_id>/
├── workspace.json            # workspace 元数据（已有）
├── files/
│   ├── _index.json           # 文件索引
│   └── uploads/              # 用户上传的文件
│       ├── 需求文档-v2.md
│       └── 2026-06-10_会议纪要.md
└── _generated/               # AI 产出
    └── 分析报告-20260610.md
```

其中 `<data_dir>` 为 `config.data_dir`（默认 `./pm_data`）。
现有 workspace 元数据文件路径为 `<data_dir>/workspaces/<ws_id>.json`，
文件存储扩展为同目录下的 `files/uploads/` 和 `files/_generated/`。

如果 workspace 配置了 `path`（服务器目录），`linked/` 仅为扫描索引，
不实际复制文件；Agent 工具直接读取原始路径。

## 3. API 设计

### 新增端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/workspaces/{id}/files` | 获取文件列表（支持 ?type=md&q=查询） |
| POST | `/api/workspaces/{id}/files/upload` | 上传文件到工作区 |
| GET | `/api/workspaces/{id}/files/{path:path}` | 获取文件内容（响应 JSON 含 text/size/type） |
| DELETE | `/api/workspaces/{id}/files/{path:path}` | 删除文件 |
| POST | `/api/workspaces/{id}/files/sync` | 同步关联目录（当 workspace.path 不为空时） |

### FileResponse 模型

```python
class FileItem(BaseModel):
    path: str
    size: int
    type: str            # "md" | "txt" | "docx" | "xlsx" | ...
    source: str          # "upload" | "linked" | "generated"
    uploaded_at: str
    uploaded_by: str
    summary: str = ""

class FileContent(BaseModel):
    path: str
    text: str            # 文本内容（Office 文档转纯文本）
    size: int
    type: str
    truncated: bool = False    # 是否因文件过大截断
```

## 4. Agent 工具层

在 `app/agent/pm/tools.py` 中新增 6 个工具，注册到 MiningAgent 的 `pm_tools` 列表。

### 工具 1: `list_workspace_files`

```python
@tool
def list_workspace_files(
    workspace_id: str,
    pattern: str = "*",
    max_results: int = 50,
) -> str:
    """列出工作区中的文件清单。
    
    用此工具查看工作区有哪些文件可用。支持 glob 模式过滤。
    
    Args:
        workspace_id: 工作区 ID
        pattern: 文件名模式，如 "*.md"、"docs/**"、"*需求*"
        max_results: 最多返回数（默认 50）
    
    Returns:
        文件列表，每行一个文件，包含路径/大小/类型/摘要
    """
```

### 工具 2: `read_workspace_file`

```python
@tool
def read_workspace_file(
    workspace_id: str,
    file_path: str,
    max_chars: int = 8000,
) -> str:
    """读取工作区中指定文件的内容。
    
    用此工具获取文件全文来分析。.md 文件返回 Markdown 原文，
    Office 文档返回转换后的文本内容。
    
    Args:
        workspace_id: 工作区 ID
        file_path: 文件相对路径（从 list_workspace_files 获取）
        max_chars: 最大读取字符数（默认 8000）
    
    Returns:
        文件内容文本。如果文件超过 max_chars，末尾标注 [...
        truncated, 共 X 字符]
    """
```

### 工具 3: `read_file_section`

```python
@tool
def read_file_section(
    workspace_id: str,
    file_path: str,
    start_line: int = 1,
    end_line: int = 100,
) -> str:
    """读取大文件的指定行范围。对超大文件分段分析很有用。
    
    Args:
        workspace_id: 工作区 ID
        file_path: 文件相对路径
        start_line: 起始行号（从 1 开始）
        end_line: 结束行号
    
    Returns:
        指定行范围内的文本
    """
```

### 工具 4: `search_in_workspace`

```python
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
        max_results: 最多返回结果数
    
    Returns:
        搜索结果，每个文件一行，含匹配行和行号
    """
```

### 工具 5: `write_workspace_file`

```python
@tool
def write_workspace_file(
    workspace_id: str,
    file_path: str,
    content: str,
) -> str:
    """在工作区中创建或更新文件。
    
    用于 AI 生成的产出——分析报告、需求总结、会议纪要等。
    文件会自动写入工作区的 _generated/ 子目录，
    路径中的目录名会自动创建。
    
    Args:
        workspace_id: 工作区 ID
        file_path: 文件名（如 "分析报告-20260610.md"）
        content: 文件内容
    
    Returns:
        文件已写入的相对路径
    """
```

### 工具 6: `get_workspace_info`

```python
@tool
def get_workspace_info(
    workspace_id: str,
) -> str:
    """获取当前工作区的整体概况。
    
    返回：项目名称/描述、文件总数及类型分布、关联目录、
    工作区内的所有会话信息。
    
    Args:
        workspace_id: 工作区 ID
    
    Returns:
        工作区概览文本
    """
```

### 工具注册

```python
# MiningAgent.__init__() 中新增
self.pm_tools = [
    retrieve_knowledge,
    get_current_time,
    update_requirement_profile,
    get_profile_summary,
    set_pending_questions,
    evaluate_sufficiency,
    # 新增文件工具
    list_workspace_files,
    read_workspace_file,
    read_file_section,
    search_in_workspace,
    write_workspace_file,
    get_workspace_info,
]
```

### 依赖: 文件工具需访问 DataStore

当前 tools.py 使用 module 级 `_datastore` 变量。
文件工具需要从 workspace_id 解析出文件存储路径。
工具函数内部通过 `_datastore` 获取路径信息。

## 5. 上下文注入机制

### 被动注入

在 `PMAgentService.chat()` 中，当 `workspace_id` 非空且 workspace
有文件时，自动向系统 prompt 追加文件上下文信息：

```python
# PMAgentService.chat() 中
workspace_context = ""
if workspace_id:
    ws = await self._ds.get_workspace(workspace_id)
    files = await self._ds.list_workspace_files(workspace_id)
    if files:
        # 注入轻量上下文：仅列出文件清单
        lines = [f"- {f['path']} ({f['type']}, {f['size']}B)" for f in files[:20]]
        workspace_context = (
            f"当前工作区「{ws['name']}」包含以下文件：\n"
            + "\n".join(lines)
            + "\n\n用户可能会要求你分析这些文件。"
              "使用 list_workspace_files / read_workspace_file 等工具查阅。"
        )

# 通过 chat_with_context 的 context_messages 注入
if workspace_context:
    context_messages.append({"role": "system", "content": workspace_context})
```

三种上下文模式：

| 模式 | 触发 | 注入内容 | Token 成本 |
|------|------|---------|-----------|
| **轻量** | 默认 | 文件清单（名称+类型+大小） | ~200-500 |
| **中等** | 用户提及文件 | 文件清单 + 所有 .md 文件摘要 | ~1000-3000 |
| **全量** | 显式请求分析 | 文件清单 + 关键文件全文 | ~5000+ |

### 主动提示

当 workspace 有新上传文件时，SSE 事件流增加提示：

```json
{"type": "workspace_update", "data": {
  "action": "file_uploaded",
  "filename": "需求文档-v2.md",
  "suggestion": "检测到新的需求文档，是否需要我分析此文件？"
}}
```

前端 ChatArea 展示为一个 QuickReply 按钮供用户点击。

## 6. 前端改动

### 6.1 WorkspaceDetail — 新增「文件」Tab

在现有 Tabs（会话列表 / Wiki 文库 / 需求图谱）中插入：

```vue
<el-tab-pane label="📁 文件" name="files">
  <FileManager :workspace-id="route.params.id as string" />
</el-tab-pane>
```

`FileManager` 组件结构：

```
FileManager.vue
├── 顶部操作栏
│   ├── 上传按钮 + 拖拽区域
│   ├── 关联目录按钮（输入服务器路径）
│   └── 搜索输入框（按文件名/类型过滤）
├── 文件列表（表格或卡片视图）
│   └── 每行：文件名 | 类型标签 | 大小 | 来源(上传/同步) | 上传时间 | 操作
│       └── 操作: 预览 / 分析 / 重命名 / 删除
├── 文件预览弹窗（支持 Markdown 渲染 + 纯文本）
└── 空状态: "暂无文件，请上传或关联目录"
```

### 6.2 ChatArea — 文件上下文指示器

在对话顶部（消息列表上方）增加恒定的上下文栏:

```vue
<div v-if="workspaceInfo && workspaceInfo.fileCount > 0" class="ws-context-bar">
  <span class="ws-context-icon">📁</span>
  <span>{{ workspaceInfo.name }} ({{ workspaceInfo.fileCount }} 个文件)</span>
  <el-button text size="small" @click="showWorkspaceFiles = true">查看文件</el-button>
</div>
```

### 6.3 文件预览 + 分析入口

预览弹窗支持:
- `.md` — Markdown 渲染
- `.txt` — 纯文本显示
- `.docx` — python-docx → 文本显示
- `.xlsx` — 表格转文本显示
- 弹窗底部 "让 AI 分析此文件" 按钮 → 注入到对话上下文

### 6.4 ChatInput — @ 引用文件

在输入框增加 `@` 触发文件选择（Phase 2）:

```
输入: @需求   →  下拉显示匹配文件
选择文件后 →  输入框插入 [@需求文档-v2.md]
发送时     →  将引用文件内容作为 context_messages 注入
```

### 6.5 改进上传对话框

现有的 ImportDialog 升级为通用的文件上传入口:

- 支持多文件上传
- 上传完成后提供选项: "AI 分析文件" / "仅保存"
- 文件上传后自动出现在 Workspace 的文件列表中

## 7. 文件解析

### 支持的文件类型

| 类型 | 解析方式 | 依赖 |
|------|---------|------|
| .md, .txt, .json, .yaml | 直接 UTF-8 读取 | 无额外依赖 |
| .docx | python-docx → 提取段落文本 | `python-docx` |
| .xlsx | openpyxl → 提取单元格文本 | `openpyxl` |
| .pptx | python-pptx → 提取文本框文本 | `python-pptx`（Phase 2） |

### 解析管线

```
上传文件 → validate_upload() → 
  根据类型分发:
    .md/.txt → 直接 UTF-8 解码
    .docx    → DocxParser.parse(file_path) → 纯文本
    .xlsx    → XlsxParser.parse(file_path) → 纯文本（每行一个单元格内容）
  → 写入工作区存储目录
  → 更新 _index.json（含自动生成的 summary = 首 100 字）
```

### 解析器代码位置

`app/core/file_handler.py` 新增 `parse_docx()`, `parse_xlsx()` 函数。

### pyproject.toml 新增依赖

```toml
[project.optional-dependencies]
office = ["python-docx>=1.1.0", "openpyxl>=3.1.0", "python-pptx>=0.6.23"]
```

Office 解析为可选依赖，不强制安装。

## 8. 错误处理

| 场景 | 处理 |
|------|------|
| 上传文件超过 10MB | 拒绝，返回 413 |
| Office 文件解析失败 | 返回错误 + 建议转为 .md 上传 |
| 文件路径含 `..` 穿越 | 拒绝，安全校验 |
| 工作区无文件时调用工具 | 工具返回 "工作区暂无文件" |
| 文件被删除后读取 | 工具返回 "文件不存在" |
| 关联目录无法访问 | 同步 API 返回错误，索引保持上一次快照 |

### 安全约束

1. 文件路径必须通过 `_validate_file_path()` 校验，拒绝 `../` 穿越
2. 上传文件大小限制: 10MB（可配置）
3. 上传文件类型白名单: `.md`, `.txt`, `.json`, `.yaml`, `.docx`, `.xlsx`
4. 写入路径限制: 只能在 `_generated/` 子目录下写入
5. 关联目录路径必须为绝对路径，且必须在允许的根路径下（可配置）

## 9. 版本规划

### Phase 1 (P0) — 核心可运行

- [ ] Workspace 数据模型扩展（path 等字段）
- [ ] 文件索引存储 + CRUD
- [ ] API 端点: 文件列表/上传/读取/删除
- [ ] Agent 工具: list + read + section + search + write + info（6 个）
- [ ] 前端「文件」Tab 基本功能（列表 + 上传 + 预览 .md）
- [ ] 轻量上下文注入
- [ ] Office 文件解析（python-docx + openpyxl）
- [ ] 中/全量上下文注入

### Phase 2 (P1) — 体验完善

- [x] PPTX 文件解析 + 图片元数据提取
- [ ] 关联服务器目录 + 手动同步 + 后台轮询
- [ ] 右侧文件树边栏（替代 ProfilePanel 位置）
- [ ] TopBar 完整度按钮 → el-drawer 展示 ProfilePanel
- [ ] ChatInput @ 引用文件 + ⊕ 引用按钮
- [ ] ChatRequest 模型扩展 referenced_files 字段

### Phase 3 (P2) — 智能增强

- [ ] Agent 主动建议分析
- [ ] 文件间交叉引用图谱
- [ ] 语义搜索（向量化文件名和摘要）

## 10. 验收标准 (P0)

- [ ] P0: `POST  /api/workspaces/{id}/files/upload` 上传 .md 文件返回 201，文件可列出
- [ ] P0: `GET  /api/workspaces/{id}/files` 返回文件列表，包含正确的大小/类型/来源
- [ ] P0: `GET  /api/workspaces/{id}/files/{path}` 返回文件文本内容
- [ ] P0: `DELETE /api/workspaces/{id}/files/{path}` 删除文件返回 200
- [ ] P0: Agent 在对话中调用 `list_workspace_files` 返回工作区文件列表
- [ ] P0: Agent 在对话中调用 `read_workspace_file` 读取并理解文件内容
- [ ] P0: Agent 在对话中调用 `search_in_workspace` 搜索关键词定位文件
- [ ] P0: Agent 在对话中调用 `write_workspace_file` 写入分析报告
- [ ] P0: Agent 在对话中调用 `get_workspace_info` 返回工作区概况
- [ ] P0: 上传 .docx 文件自动解析为文本，Agent 可读
- [ ] P0: 前端 workspace 详情页「文件」Tab 正常展示和上传
- [ ] P0: 前端文件预览弹窗正确渲染 .md 文件
- [ ] P0: 上传超过 10MB 文件返回 413
- [ ] P0: 文件路径穿越攻击被拦截

## 11. 风险与注意事项

- **文件系统与 workspace 不一致**: JSON 回退模式下，文件操作依赖本地文件系统；
  MySQL 模式下，文件路径存储在数据库中。切换存储后端时文件索引不受影响。
- **大文件上下文爆炸**: 默认 max_chars=8000 限制，Agent 分段读取。
- **Office 解析可选依赖**: 如果未安装 python-docx/openpyxl，上传 Office 文件返回 400
  并提示安装。
- **并发写入**: _index.json 使用现有的 _FileLock 机制同步。
- **上下文预算**: 轻量注入控制在 500 token 以内，不显著减少对话预算。
