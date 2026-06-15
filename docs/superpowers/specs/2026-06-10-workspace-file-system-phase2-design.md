# Spec: 工作区文件系统 Phase 2 — 体验完善

> 日期: 2026-06-10
> 状态: 定稿 ✓

## 4 个功能

### F1: 图片/PPTX 文件解析

**文件类型白名单** — ALLOWED_EXTENSIONS 扩展为：

```
{".md", ".txt", ".json", ".yaml", ".yml", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}
```

**解析管线** — `app/core/workspace_files.py` 新增：
- `parse_pptx(file_path)` — 遍历所有 slide 的 shape.text + table 文本，返回纯文本
- `parse_image(file_path)` — Pillow 提取图片元数据（格式、尺寸、模式），不做 OCR
- 扩展 `is_text_file()` → 改为 `is_parseable_text_file()` 或保持原有 + 独立 `is_image_file()`
- `read_file()` 中处理 pptx/image 分支

**依赖**：
```toml
[project.optional-dependencies]
office = ["python-docx>=1.1.0", "python-pptx>=0.6.23"]
```

### F2: 关联服务器目录 + 手动同步 + 后台轮询

**WorkspaceFileManager 新增方法**：
- `link_directory(dir_path)` — 关联目录 + 首次扫描 + 写入索引（source="linked", abs_path=原始路径）
- `unlink_directory()` — 解除关联，移除所有 linked 条目
- `sync_linked()` — 扫描目录 diff 索引，返回变更摘要 `{added, removed, updated, unchanged}`
- `start_watcher(interval=300)` — 启动后台线程轮询（threading + Event 控制）
- `stop_watcher()` — 停止轮询

**后台轮询**：
- 线程函数每 interval 秒调用 `sync_linked()`
- 通过 `threading.Event` 控制停止
- 服务启动时遍历已有 linked workspace 启动 watcher（`PMAgentService.__init__`）

**同步流程**：
1. 递归扫描 `dir_path` 中所有白名单扩展名的文件
2. 对每个文件记录 `(相对路径, mtime, size, abs_path)`
3. 与 `_index.json` 中 source="linked" 的条目 diff
4. 批处理更新索引（新增/移除/更新）

**API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/workspaces/{id}/link` | 绑定目录 + 首次扫描，body: `{path: "/data/projects"}` |
| POST | `/api/workspaces/{id}/unlink` | 解除目录绑定 |
| POST | `/api/workspaces/{id}/sync` | 手动同步，返回变更摘要 |
| GET | `/api/workspaces/{id}/linked-status` | 查看同步状态 |

### F3: 右侧文件树边栏 + TopBar 完整度按钮

**布局改动** — `AppLayout.vue`：
- 右侧 ProfilePanel 替换为 FileTreePanel
- TopBar 增加「📊 N%」完整度按钮
- 点击完整度按钮 → `el-drawer` 弹出展示 ProfilePanel

**FileTreePanel 组件**（新增）：
- 宽度 260px，高度 100vh，固定右侧
- 当前 workspace 名称 + 上传按钮（顶部）
- 按目录结构展开的文件树
- 文件行：类型图标 + 文件名 + 大小 + ⊕ 引用按钮(hover)
- AI 生成文件带绿色「AI」标签
- 已引用文件标记 + 底部「当前引用」区域
- 底部同步状态信息

**Props**：`workspaceId: string`, `referencedFiles: string[]`
**Emits**：`reference(filePath)`, `removeReference(filePath)`

**TopBar 改动**：
- 新增 `sufficiencyPercent prop`
- 新增 `showProfile` emit
- 显示「📊 N%」按钮(百分比 > 0 时)
- 点击 emit `showProfile`

**AppLayout 逻辑**：
- 引入 `referencedFiles` ref
- `handleFileReference` / `handleRemoveReference` 方法
- 将 referencedFiles 透传给 ChatArea → ChatInput

### F4: @ 引用文件 + ⊕ 引用 + 后端注入

**@ 引用** — ChatInput.vue：
1. 检测 `@` 字符（当前输入末尾）
2. 弹出文件搜索面板，调用 `fetchWorkspaceFiles(wsId)`
3. 文字过滤文件列表
4. 选择后追加到 referencedFiles，输入框上方显示蓝色引用标签

**⊕ 引用** — FileTreePanel.vue：
1. 文件行 hover 出现 ⊕ 按钮
2. 点击 emit `reference(filePath)`
3. 已引用的文件标记为选中态

**后端模型扩展**：
```python
# app/models/pm.py
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    workspace_id: str = ""
    referenced_files: list[str] = Field(default=[], description="引用的工作区文件路径列表")

class AgentRequest(BaseModel):
    message: str
    session_id: str = "default"
    mode: str = "one_shot"
    use_knowledge: bool = False
    workspace_id: str = ""
    referenced_files: list[str] = Field(default=[])
```

**后端注入** — `PMAgentService.chat()` 中处理引用文件：
- 遍历 `referenced_files`
- 调用 `read_workspace_file` 读取内容
- 构造 `context_messages` 注入到 agent

**前端 API** — `ChatArea.vue` → `readSSEStream` 的 body 中加入 `referenced_files`
**ChatView.vue** → `handleSend` 中从 AppLayout 获取 referencedFiles

## 验收标准

- [ ] P0: 上传 .pptx 文件自动解析为文本
- [ ] P0: 上传 .png/.jpg 文件成功，Agent 可读元数据
- [ ] P0: POST /api/workspaces/{id}/link 绑定目录并首次扫描
- [ ] P0: POST /api/workspaces/{id}/sync 返回变更摘要
- [ ] P0: POST /api/workspaces/{id}/unlink 移除所有 linked 文件
- [ ] P0: 右侧边栏显示当前 workspace 文件树
- [ ] P0: 切换左侧 workspace 时右侧文件树自动更新
- [ ] P0: 点击文件 ⊕ 按钮 → 文件引用到对话
- [ ] P0: TopBar 显示「📊 N%」完整度按钮
- [ ] P0: 点击完整度按钮 → 弹出抽屉显示画像
- [ ] P0: 输入 @ 可搜索并引用文件
- [ ] P0: 引用文件内容注入到 Agent 对话上下文
