# 工作区文件系统 Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** PPTX/Image 解析、目录关联同步、右侧文件树边栏 + TopBar 完整度按钮、@ 引用文件

**Architecture:** 后端扩展解析管线 + 目录同步机制，前端新增 FileTreePanel 组件替换右侧 ProfilePanel，TopBar 加完整度按钮触发展示

---

### Task 1: PPTX/Image 文件解析管线

**Files:**
- Modify: `app/core/workspace_files.py` (新增 parse_pptx, parse_image, 扩展文件类型检测)
- Modify: `app/core/file_handler.py` (扩展 ALLOWED_EXTENSIONS)

**app/core/file_handler.py:17**:
```python
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}
```

**app/core/workspace_files.py** — 新增以下内容（在 Office parsing 区域后追加）：

```python
# ── PPTX parsing (optional) ──

_HAS_PPTX = False
try:
    import pptx as _pptx_module
    _HAS_PPTX = True
except ImportError:
    pass


def parse_pptx(file_path: str | Path) -> str:
    """Extract all text from .pptx slides."""
    if not _HAS_PPTX:
        raise RuntimeError("python-pptx not installed. Run: pip install python-pptx")
    prs = _pptx_module.Presentation(str(file_path))
    lines = []
    for i, slide in enumerate(prs.slides, 1):
        lines.append(f"--- Slide {i} ---")
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                lines.append(shape.text)
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [cell.text for cell in row.cells]
                    lines.append(" | ".join(cells))
    return "\n".join(lines)


_HAS_PIL = False
try:
    from PIL import Image as _PIL_Image
    _HAS_PIL = True
except ImportError:
    pass


def parse_image(file_path: str | Path) -> str:
    """Extract metadata from an image file. Returns text description."""
    if not _HAS_PIL:
        raise RuntimeError("Pillow not installed. Run: pip install Pillow")
    img = _PIL_Image.open(str(file_path))
    return (
        f"[图片: {Path(file_path).name}]\n"
        f"格式: {img.format}\n"
        f"尺寸: {img.width}x{img.height}\n"
        f"模式: {img.mode}\n"
        f"\n如需分析图片内容，请使用 LLM 的视觉分析能力。"
    )


def is_image_ext(ext: str) -> bool:
    return ext in ("png", "jpg", "jpeg", "gif", "bmp")


def is_office_ext(ext: str) -> bool:
    return ext in ("docx", "xlsx", "pptx")
```

**修改 `is_text_file()` → 保留原有，新增 `_get_file_parser()` 模式**：
实际上更好的做法是在 `read_file()` 中增加 `elif ext == "pptx"` 和 `elif is_image_ext(ext)` 分支。

修改 `read_file()` 方法中的文件读取逻辑（约第 137-144 行）：

```python
        if is_text_file(ext):
            text = file_path.read_text(encoding="utf-8", errors="replace")
        elif ext == "docx":
            text = parse_docx(file_path)
        elif ext == "xlsx":
            try:
                text = parse_xlsx(file_path)
            except Exception:
                text = f"[无法解析 xlsx 文件: {relative_path}]"
        elif ext == "pptx":
            text = parse_pptx(file_path)
        elif is_image_ext(ext):
            text = parse_image(file_path)
        else:
            text = file_path.read_text(encoding="utf-8", errors="replace")
```

**pyproject.toml** — 在 optional-dependencies 中添加 office 组：

```toml
[project.optional-dependencies]
dev = [...]
office = ["python-docx>=1.1.0", "python-pptx>=0.6.23"]
```

- [ ] **Step 1**: 修改 file_handler.py ALLOWED_EXTENSIONS
- [ ] **Step 2**: 修改 workspace_files.py 新增解析函数 + read_file 分支
- [ ] **Step 3**: 修改 pyproject.toml 可选依赖
- [ ] **Step 4**: 验证导入
- [ ] **Step 5**: Commit

---

### Task 2: 关联目录同步 (后端)

**Files:**
- Modify: `app/core/workspace_files.py` (新增 link/sync/watcher 方法)
- Modify: `app/db/__init__.py` (新增 DataStore 抽象)
- Modify: `app/db/compat.py` (FileDataStore 实现)
- Modify: `app/db/repository.py` (MySQLDataStore 实现)
- Modify: `app/api/workspace.py` (新增 link/unlink/sync/linked-status 端点)

**WorkspaceFileManager 新增方法**（在 delete_file 之后、get_info 之前插入）：

```python
    # ── Directory linking ──

    def link_directory(self, dir_path: str) -> dict:
        """Associate a server directory with this workspace."""
        p = Path(dir_path)
        if not p.is_dir():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        abs_path = str(p.resolve())

        # Write link info to workspace metadata
        ws_dir = Path(config.data_dir) / "workspaces" / self._ws_id
        meta_file = ws_dir / ".linked_path"
        meta_file.write_text(abs_path, encoding="utf-8")

        # First scan
        result = self._do_scan(abs_path)
        self.start_watcher()
        return result

    def unlink_directory(self) -> dict:
        """Remove directory link and all linked files from index."""
        self.stop_watcher()
        ws_dir = Path(config.data_dir) / "workspaces" / self._ws_id
        meta_file = ws_dir / ".linked_path"
        if meta_file.exists():
            meta_file.unlink()

        index = _load_index(self._files_dir)
        linked = [f for f in index if f.get("source") == "linked"]
        index = [f for f in index if f.get("source") != "linked"]
        _save_index(self._files_dir, index)
        return {"removed": len(linked)}

    def sync_linked(self) -> dict:
        """Full sync: scan linked dir, diff index, return changes."""
        ws_dir = Path(config.data_dir) / "workspaces" / self._ws_id
        meta_file = ws_dir / ".linked_path"
        if not meta_file.exists():
            return {"error": "No linked directory"}
        abs_path = meta_file.read_text(encoding="utf-8").strip()
        if not Path(abs_path).is_dir():
            return {"error": f"Linked directory not found: {abs_path}"}
        return self._do_scan(abs_path)

    def _do_scan(self, abs_path: str) -> dict:
        """Scan directory and diff with index."""
        allowed = {".md", ".txt", ".json", ".yaml", ".yml", ".docx", ".xlsx", ".pptx",
                   ".png", ".jpg", ".jpeg", ".gif", ".bmp"}
        base = Path(abs_path)
        scanned: dict[str, dict] = {}

        for f in base.rglob("*"):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext not in allowed:
                continue
            rel = str(f.relative_to(base))
            stat = f.stat()
            scanned[rel] = {
                "path": rel, "size": stat.st_size, "type": ext.lstrip("."),
                "source": "linked", "abs_path": str(f.resolve()),
                "mtime": stat.st_mtime, "uploaded_at": _now(),
                "summary": rel,
            }

        index = _load_index(self._files_dir)
        existing = {e["path"]: e for e in index if e.get("source") == "linked"}

        added, removed, updated, unchanged = [], [], [], 0
        for path, info in scanned.items():
            if path not in existing:
                added.append(path)
            elif existing[path].get("mtime", 0) != info["mtime"] or existing[path].get("size", 0) != info["size"]:
                updated.append(path)
            else:
                unchanged += 1

        for path in existing:
            if path not in scanned:
                removed.append(path)

        # Rebuild index: keep non-linked + new scanned
        new_index = [e for e in index if e.get("source") != "linked"]
        new_index.extend(scanned.values())
        _save_index(self._files_dir, new_index)

        logger.info(f"[ws sync] {abs_path}: +{len(added)} ~{len(updated)} -{len(removed)} ={unchanged}")
        return {"added": added, "removed": removed, "updated": updated, "unchanged": unchanged,
                "total": len(scanned)}

    def get_linked_status(self) -> dict:
        ws_dir = Path(config.data_dir) / "workspaces" / self._ws_id
        meta_file = ws_dir / ".linked_path"
        if not meta_file.exists():
            return {"linked": False}
        path = meta_file.read_text(encoding="utf-8").strip()
        index = _load_index(self._files_dir)
        linked_count = len([f for f in index if f.get("source") == "linked"])
        return {"linked": True, "path": path, "file_count": linked_count,
                "dir_exists": Path(path).is_dir()}
```

**Threading — 在模块级别添加 watcher 管理**（在 WorkspaceFileManager 类定义之前或之后）：

```python
import threading
import time

_watchers: dict[str, threading.Thread] = {}
_watcher_stop: dict[str, threading.Event] = {}
_watcher_lock = threading.Lock()


def start_watcher(workspace_id: str, interval: int = 300) -> None:
    with _watcher_lock:
        stop_watcher(workspace_id)
        stop_event = threading.Event()
        t = threading.Thread(
            target=_watcher_loop,
            args=(workspace_id, interval, stop_event),
            daemon=True,
            name=f"ws-watcher-{workspace_id[:8]}",
        )
        _watcher_stop[workspace_id] = stop_event
        _watchers[workspace_id] = t
        t.start()
        logger.info(f"[ws watcher] Started for {workspace_id} (interval={interval}s)")


def stop_watcher(workspace_id: str) -> None:
    with _watcher_lock:
        if workspace_id in _watcher_stop:
            _watcher_stop[workspace_id].set()
        if workspace_id in _watchers:
            _watchers[workspace_id].join(timeout=5)
            del _watchers[workspace_id]
        _watcher_stop.pop(workspace_id, None)


def _watcher_loop(workspace_id: str, interval: int, stop: threading.Event) -> None:
    from app.core.workspace_files import WorkspaceFileManager
    while not stop.wait(interval):
        try:
            fm = WorkspaceFileManager(workspace_id)
            result = fm.sync_linked()
            if result.get("added") or result.get("removed") or result.get("updated"):
                logger.info(f"[ws watcher] {workspace_id} changes detected: {result}")
        except Exception as e:
            logger.debug(f"[ws watcher] {workspace_id} sync error: {e}")
```

注意：`WorkspaceFileManager.__init__` 需要记录 `self._ws_id`：

```python
    def __init__(self, workspace_id: str):
        self._ws_id = workspace_id
        ws_dir = Path(config.data_dir) / "workspaces" / workspace_id
        ...
```

**DataStore 抽象** — 在 `app/db/__init__.py` 添加：

```python
    @abstractmethod
    async def link_workspace_directory(self, workspace_id: str, dir_path: str) -> dict:
        """Link a server directory to workspace and scan."""

    @abstractmethod
    async def unlink_workspace_directory(self, workspace_id: str) -> dict:
        """Unlink directory and remove linked files."""

    @abstractmethod
    async def sync_workspace_files(self, workspace_id: str) -> dict:
        """Manual sync linked directory."""

    @abstractmethod
    async def get_workspace_linked_status(self, workspace_id: str) -> dict:
        """Get link status."""
```

**compat.py 和 repository.py 实现**——委托给 WorkspaceFileManager。

**API 端点** — 在 `app/api/workspace.py` 添加：

```python
@router.post("/workspaces/{workspace_id}/link")
async def ws_link_dir(
    workspace_id: str,
    body: dict,  # {path: "/data/projects"}
    current_user: dict = Depends(get_current_user),
):
    ds = _ds()
    ws = await ds.get_workspace(workspace_id)
    if ws is None: raise HTTPException(404, "Workspace not found")
    try:
        result = await ds.link_workspace_directory(workspace_id, body["path"])
        return {"success": True, "result": result}
    except FileNotFoundError as e:
        raise HTTPException(400, detail=str(e))

@router.post("/workspaces/{workspace_id}/unlink")
async def ws_unlink_dir(...):
    ...

@router.post("/workspaces/{workspace_id}/sync")
async def ws_sync_files(...):
    ...

@router.get("/workspaces/{workspace_id}/linked-status")
async def ws_linked_status(...):
    ...
```

- [ ] **Step 1**: WorkspaceFileManager 新增 link/sync 方法
- [ ] **Step 2**: 模块级 watcher 线程管理
- [ ] **Step 3**: DataStore 抽象 + 双实现
- [ ] **Step 4**: API 端点 4 个
- [ ] **Step 5**: 验证
- [ ] **Step 6**: Commit

---

### Task 3: 右侧文件树边栏 + TopBar 完整度按钮

**Files:**
- Create: `reqcollect-web/src/components/workspace/FileTreePanel.vue`
- Modify: `reqcollect-web/src/views/WorkspaceDetail.vue` (FileManager 的面板也可以放文件树视图，但暂且保留)
- Modify: `reqcollect-web/src/components/layout/AppLayout.vue`
- Modify: `reqcollect-web/src/components/layout/TopBar.vue`

**FileTreePanel.vue** — 全新建组件（右对齐面板，宽 260px）：

```vue
<template>
  <aside class="file-tree-panel">
    <!-- Header -->
    <div class="ftp-header">
      <span class="ftp-icon">📁</span>
      <span class="ftp-title">{{ workspaceName || '选择工作空间' }}</span>
      <el-button text size="small" @click="triggerUpload" class="ftp-upload-btn">+ 上传</el-button>
      <input ref="fileInput" type="file" hidden :accept="acceptStr" @change="handleUpload" />
    </div>

    <!-- File tree -->
    <div class="ftp-body">
      <div v-if="loading" v-loading="true" style="height:200px" />
      <template v-else-if="tree.length === 0">
        <div class="ftp-empty">暂无文件</div>
      </template>
      <div v-else class="ftp-tree">
        <div v-for="node in tree" :key="node.path">
          <!-- Directory node -->
          <div v-if="!node.isLeaf" class="ftp-dir" @click="node.expanded = !node.expanded">
            <span class="ftp-arrow" :class="{ open: node.expanded }">▶</span>
            <span>📂</span>
            <span class="ftp-label">{{ node.label }}</span>
            <span class="ftp-count">{{ node.children.length }}</span>
          </div>
          <!-- Children -->
          <div v-if="!node.isLeaf && node.expanded" class="ftp-children">
            <div
              v-for="child in node.children"
              :key="child.path"
              class="ftp-file"
              :class="{ referenced: isReferenced(child.path) }"
              @mouseenter="child.showRef = true"
              @mouseleave="child.showRef = false"
            >
              <span class="ftp-file-icon">{{ fileIcon(child.type) }}</span>
              <span class="ftp-file-name" @click="previewFile(child)">{{ child.label }}</span>
              <span class="ftp-file-size" v-if="child.size">{{ fmtSize(child.size) }}</span>
              <span v-if="child.source === 'generated'" class="ftp-ai-tag">AI</span>
              <button
                v-if="child.showRef || isReferenced(child.path)"
                class="ftp-ref-btn"
                @click.stop="toggleRef(child.path)"
              >{{ isReferenced(child.path) ? '✕' : '⊕' }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Referenced files -->
    <div v-if="referencedFiles.length" class="ftp-ref-section">
      <div class="ftp-ref-title">📎 当前引用</div>
      <div v-for="ref in referencedFiles" :key="ref" class="ftp-ref-item">
        <span>📝</span><span class="ftp-ref-name">{{ ref }}</span>
        <button class="ftp-ref-remove" @click="$emit('removeReference', ref)">✕</button>
      </div>
    </div>

    <!-- Footer: linked status -->
    <div class="ftp-footer">
      <span v-if="linkedStatus?.linked" class="ftp-sync-info">🔄 {{ syncLabel }}</span>
      <span v-else class="ftp-sync-info" style="color:#c0c4cc">未关联目录</span>
    </div>

    <!-- Preview dialog -->
    <el-dialog v-model="previewVisible" :title="previewTitle" width="700px" top="5vh">
      ...
    </el-dialog>
  </aside>
</template>

<script setup lang="ts">
// Props: workspaceId, referencedFiles
// Emits: reference, removeReference
//
// mount 时 fetchWorkspaceFiles → 构建 tree（按 / 分割 path）
// watch workspaceId 切换时重新加载
// ⊕ 点击 emit reference
// 上传文件后重新加载
</script>

<style scoped>
.file-tree-panel { width:260px; min-width:260px; border-left:1px solid #e5e6eb; background:#fff; display:flex; flex-direction:column; height:100vh; font-size:13px; }
.ftp-header { padding:10px 12px; border-bottom:1px solid #f0f0f5; display:flex; align-items:center; gap:6px; }
.ftp-title { flex:1; font-weight:500; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ftp-body { flex:1; overflow-y:auto; padding:4px 0; }
.ftp-dir { padding:4px 8px; display:flex; align-items:center; gap:4px; cursor:pointer; font-size:12px; color:#666; }
.ftp-dir:hover { background:#f7f8fa; }
.ftp-arrow { font-size:10px; transition:transform .15s; }
.ftp-arrow.open { transform:rotate(90deg); }
.ftp-children { }
.ftp-file { padding:3px 8px 3px 28px; display:flex; align-items:center; gap:4px; border-radius:4px; cursor:pointer; }
.ftp-file:hover { background:#f0f3f8; }
.ftp-file.referenced { background:#ecf5ff; }
.ftp-file-icon { font-size:14px; }
.ftp-file-name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; }
.ftp-file-size { font-size:10px; color:#c0c4cc; }
.ftp-ai-tag { font-size:10px; color:#67c23a; background:#f0f9eb; padding:0 4px; border-radius:3px; }
.ftp-ref-btn { font-size:12px; border:none; background:none; cursor:pointer; color:#409eff; padding:0 2px; }
.ftp-ref-section { border-top:1px solid #f0f0f5; padding:6px 12px; }
.ftp-ref-title { font-size:11px; color:#c0c4cc; margin-bottom:4px; }
.ftp-ref-item { display:flex; align-items:center; gap:4px; padding:2px 4px; font-size:12px; color:#409eff; background:#ecf5ff; border-radius:4px; margin-bottom:2px; }
.ftp-ref-name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ftp-ref-remove { border:none; background:none; cursor:pointer; font-size:11px; color:#c0c4cc; }
.ftp-footer { border-top:1px solid #f0f0f5; padding:6px 12px; font-size:11px; }
.ftp-sync-info { color:#c0c4cc; }
.ftp-empty { text-align:center; padding:40px; color:#c0c4cc; font-size:13px; }
.ftp-upload-btn { font-size:12px; }
</style>
```

**AppLayout.vue 改动**：
1. 引入 FileTreePanel 组件
2. 右侧 ProfilePanel → 替换为 FileTreePanel
3. 添加 referencedFiles 状态 + 处理方法
4. 添加 profileDrawer 控制

```typescript
// 新增
import FileTreePanel from '@/components/workspace/FileTreePanel.vue'
const referencedFiles = ref<string[]>([])
const profileDrawer = ref(false)

function handleFileReference(fp: string) {
  if (!referencedFiles.value.includes(fp))
    referencedFiles.value.push(fp)
}
function handleRemoveReference(fp: string) {
  referencedFiles.value = referencedFiles.value.filter(f => f !== fp)
}
```

模板中将原有的 ProfilePanel 区域替换：

```vue
<!-- 替换原有 -->
<FileTreePanel
  v-if="sessionStore.currentId && sessionStore.currentWorkspaceId"
  :workspace-id="sessionStore.currentWorkspaceId!"
  :referenced-files="referencedFiles"
  @reference="handleFileReference"
  @remove-reference="handleRemoveReference"
/>
<!-- Profile Drawer -->
<el-drawer v-model="profileDrawer" title="需求画像" size="360px">
  <ProfilePanel v-if="sessionStore.currentId" :profile="profileStore.profile" :percent="sufficiencyPercent" />
</el-drawer>
```

需要透传 `referencedFiles` 到 ChatArea（作为 prop 或通过 provide/inject）。

**TopBar.vue 改动**：
1. 接收 `sufficiencyPercent` prop
2. 新增 `showProfile` emit
3. 显示完整度按钮

```vue
<!-- 在标题右边增加 -->
<el-button v-if="sufficiencyPercent && sufficiencyPercent > 0"
  size="small" class="sufficiency-btn"
  @click="$emit('showProfile')"
>
  📊 {{ sufficiencyPercent }}%
</el-button>
```

```typescript
const props = defineProps<{
  title: string
  sessionId: string | null
  sufficiencyPercent: number
}>()
const emit = defineEmits<{
  showProfile: []
}>()
```

**AppLayout 中 TopBar 的 sufficiencyPercent prop** — 通过现有 profileStore 计算：

```vue
<TopBar
  :title="title"
  :session-id="sessionStore.currentId"
  :sufficiency-percent="sufficiencyPercent"
  @show-profile="profileDrawer = true"
/>
```

- [ ] **Step 1**: 创建 FileTreePanel.vue
- [ ] **Step 2**: 修改 AppLayout.vue（替换右侧边栏 + referencedFiles 状态）
- [ ] **Step 3**: 修改 TopBar.vue（完整度按钮 + showProfile emit）
- [ ] **Step 4**: 验证构建
- [ ] **Step 5**: Commit

---

### Task 4: @ 引用文件 + ⊕ 引用后端注入

**Files:**
- Modify: `reqcollect-web/src/components/chat/ChatInput.vue` (@ 引用)
- Modify: `reqcollect-web/src/components/chat/ChatArea.vue` (透传 referencedFiles)
- Modify: `reqcollect-web/src/views/ChatView.vue` (referencedFiles 传递)
- Modify: `app/models/pm.py` (扩展 referenced_files 字段)
- Modify: `app/services/pm_agent_service.py` (处理引用文件注入)
- Modify: `app/api/pm.py` (ChatRequest/AgentRequest 用到新字段)

**ChatInput.vue 改动** — 增加 @ 引用功能：

```vue
<template>
  <div class="composer-wrap">
    <div class="composer">
      <!-- Referenced file tags -->
      <div v-if="referencedFiles.length" class="ref-tags">
        <el-tag v-for="f in referencedFiles" :key="f" closable size="small"
          @close="$emit('removeReference', f)" type="primary">
          📄 {{ f }}
        </el-tag>
      </div>
      <textarea ... @input="onInput" v-model="text" />
      ...
    </div>
    <!-- @ file picker dropdown -->
    <div v-if="showFilePicker" class="file-picker-dropdown">
      <div class="fp-search">
        <input v-model="fileQuery" placeholder="搜索文件..." autofocus />
      </div>
      <div class="fp-list">
        <div v-for="f in filteredFiles" :key="f.path" class="fp-item"
          @click="selectFile(f)">
          <span>{{ fileIcon(f.type) }}</span>
          <span class="fp-name">{{ f.path }}</span>
          <span class="fp-type">{{ f.type }}</span>
        </div>
        <div v-if="filteredFiles.length === 0" class="fp-empty">无匹配文件</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 监听 text 中的 @ 符号
// 当 @ 在末尾（[空格]@ 或行首 @）时弹出文件选择器
// 选择文件后：将 @ 替换为文件引用标签，隐藏选择器
// 发送时：extract 文件名到 referencedFiles 列表

// Props: referencedFiles, workspaceId
// Emits: reference(filePath), removeReference(filePath)

const props = defineProps<{
  disabled: boolean
  mode: string
  sessionId: string | null
  referencedFiles: string[]
  workspaceId: string | null
}>()

const emit = defineEmits<{
  send: [text: string]
  toggleMode: []
  fileUpload: [file: File]
  reference: [filePath: string]
  removeReference: [filePath: string]
}>()

const text = ref('')
const showFilePicker = ref(false)
const fileQuery = ref('')
const allFiles = ref<any[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

async function onInput() {
  // Detect @ at end of text
  const lastChar = text.value[text.value.length - 1]
  const prevChar = text.value[text.value.length - 2]
  if (lastChar === '@' && (!prevChar || prevChar === ' ')) {
    await loadFiles()
    fileQuery.value = ''
    showFilePicker.value = true
  }
  // Hide if we backspace away from @
  if (showFilePicker.value && !text.value.includes('@')) {
    showFilePicker.value = false
  }
}

function selectFile(f: any) {
  // Remove the @ from text
  text.value = text.value.replace(/@$/, '').replace(/ @$/, '')
  showFilePicker.value = false
  emit('reference', f.path)
}
</script>
```

**ChatArea.vue 改动** — 透传 referencedFiles 和 workspaceId：

```vue
<ChatInput
  :disabled="streaming"
  :mode="mode"
  :session-id="sessionId"
  :referenced-files="referencedFiles"
  :workspace-id="workspaceId"
  @send="(v) => $emit('send', v)"
  @toggle-mode="$emit('toggleMode')"
  @file-upload="handleFileUpload"
  @reference="(fp) => $emit('reference', fp)"
  @remove-reference="(fp) => $emit('removeReference', fp)"
/>
```

**ChatView.vue 改动** — 传递 referencedFiles + 引用处理到 SSE：

```typescript
// props 从 AppLayout 通过 provide/inject 获取 referencedFiles
const referencedFiles = inject<Ref<string[]>>('referencedFiles', ref([]))

async function handleSend(text: string) {
  // ...
  readSSEStream({
    message: text,
    session_id: sid,
    mode: mode.value,
    use_knowledge: false,
    workspace_id: sessionStore.currentWorkspaceId || '',
    referenced_files: referencedFiles.value,  // 新增
  }, ...)
  // 清空引用
  referencedFiles.value = []
}
```

**app/models/pm.py** — 扩展 ChatRequest 和 AgentRequest：

```python
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    use_knowledge: bool = False
    workspace_id: str = ""
    referenced_files: list[str] = Field(default=[], description="引用的工作区文件路径")


class AgentRequest(BaseModel):
    message: str
    session_id: str = "default"
    mode: str = "one_shot"
    use_knowledge: bool = False
    workspace_id: str = ""
    referenced_files: list[str] = Field(default=[])
```

**PMAgentService.chat() 改动** — 在 `chat()` 方法签名中添加 `referenced_files: list[str] | None = None`，在构建 context_messages 时注入引用文件内容：

```python
    async def chat(
        self,
        message: str,
        thread_id: str = "default",
        user_id: str | None = None,
        workspace_id: str | None = None,
        use_knowledge: bool = False,
        referenced_files: list[str] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
```

在 `session = await self._ds.get_session(thread_id)` 之后，注入引用文件：

```python
        # Inject referenced file contents
        if referenced_files and workspace_id:
            for rel_path in referenced_files:
                try:
                    content = await self._ds.read_workspace_file(workspace_id, rel_path, max_chars=8000)
                    context_messages.append({
                        "role": "system",
                        "content": f"[用户引用了工作区文件: {rel_path}]\n\n{content['text']}"
                    })
                except (FileNotFoundError, RuntimeError) as e:
                    logger.warning(f"[{thread_id}] Failed to read referenced file {rel_path}: {e}")
```

**api/pm.py 改动** — 将 `referenced_files` 从 request 模型传到 service：

```python
# pm_chat 和 pm_agent 端点中
async for event in _svc().chat(
    request.message,
    request.session_id,
    user_id=current_user["id"],
    workspace_id=request.workspace_id or None,
    use_knowledge=request.use_knowledge,
    referenced_files=request.referenced_files,  # 新增
):
```

- [ ] **Step 1**: ChatInput.vue @ 引用
- [ ] **Step 2**: ChatArea/ChatView 透传
- [ ] **Step 3**: 后端模型扩展
- [ ] **Step 4**: PMAgentService 注入
- [ ] **Step 5**: API 端点传参
- [ ] **Step 6**: 验证
- [ ] **Step 7**: Commit
