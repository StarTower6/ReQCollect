# Wiki 页面功能（基础版）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在工作空间内实现 Wiki 页面 CRUD + Markdown 编辑器 + 页面列表

**Architecture:** DataStore 协议新增 5 个 wiki 抽象方法 → FileDataStore + MySQLDataStore 双实现 → API 路由层 → Vue 前端（阅读页 + 编辑器 + WorkspaceDetail tab）

**Tech Stack:** Python/FastAPI + SQLAlchemy (asyncmy) + Vue 3 + Pinia + Element Plus + marked.js

---

### Task 1: DataStore 协议扩展

**Files:**
- Modify: `app/db/__init__.py`

- [ ] **Step 1: 在 Workspaces 区域后新增 Wiki 协议方法**

在 `app/db/__init__.py` 的 `# ── Workspaces ──` 区域之后、`# ── Audit ──` 之前插入：

```python
    # ── Wiki Pages ──

    @abstractmethod
    async def create_wiki_page(
        self,
        workspace_id: str,
        title: str,
        content: str = "",
        created_by: str = "",
    ) -> dict:
        """Create a wiki page and return its dict."""

    @abstractmethod
    async def get_wiki_page(self, page_id: str) -> dict | None:
        """Get wiki page by ID."""

    @abstractmethod
    async def list_wiki_pages(self, workspace_id: str) -> list[dict]:
        """List all wiki pages in a workspace."""

    @abstractmethod
    async def update_wiki_page(self, page_id: str, **kwargs) -> dict | None:
        """Update wiki page fields."""

    @abstractmethod
    async def delete_wiki_page(self, page_id: str) -> bool:
        """Delete a wiki page."""
```

- [ ] **Step 2: 提交**

```bash
git add app/db/__init__.py
git commit -m "feat: add wiki page CRUD methods to DataStore protocol"
```

---

### Task 2: WikiPage ORM 模型 + MySQL 迁移

**Files:**
- Modify: `app/db/models.py`
- Modify: `app/db/database.py`

- [ ] **Step 1: 在 app/db/models.py 的 Workspace 类之后插入 WikiPage**

在 `Workspace` 类定义之后、`# ── Audit Log ──` 之前插入：

```python
# ── Wiki Page ──


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_wiki_workspace", "workspace_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "title": self.title or "",
            "content": self.content or "",
            "created_by": self.created_by,
            "updated_by": self.updated_by or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
```

- [ ] **Step 2: 在 app/db/database.py 中添加 idempotent CREATE TABLE 迁移**

在 `# Apply idempotent migrations` 区块中、`ALTER TABLE sessions` 迁移之后添加：

```python
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "CREATE TABLE IF NOT EXISTS wiki_pages ("
                        "id VARCHAR(64) PRIMARY KEY, "
                        "workspace_id VARCHAR(64) NOT NULL, "
                        "title VARCHAR(255) NOT NULL, "
                        "content TEXT, "
                        "created_by VARCHAR(64) NOT NULL, "
                        "updated_by VARCHAR(64) DEFAULT '', "
                        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                        "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
                        "INDEX idx_wiki_workspace (workspace_id)"
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
                    )
                )
                logger.info("Applied migration: wiki_pages table")
            except Exception:
                logger.debug("Migration: wiki_pages table already exists")
```

- [ ] **Step 3: 提交**

```bash
git add app/db/models.py app/db/database.py
git commit -m "feat: add WikiPage ORM model and idempotent MySQL migration"
```

---

### Task 3: FileDataStore Wiki 实现

**Files:**
- Modify: `app/db/compat.py`

- [ ] **Step 1: 在 `# ── Workspaces ──` 区域之后新增 `# ── Wiki Pages ──`**

```python
    # ── Wiki Pages ──

    def _wiki_path(self, workspace_id: str) -> Path:
        p = self._base / "wiki" / workspace_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _wiki_file(self, workspace_id: str, page_id: str) -> Path:
        return self._wiki_path(workspace_id) / f"{page_id}.json"

    async def create_wiki_page(
        self,
        workspace_id: str,
        title: str,
        content: str = "",
        created_by: str = "",
    ) -> dict:
        import uuid
        now = _now()
        page_id = uuid.uuid4().hex[:16]
        data = {
            "id": page_id,
            "workspace_id": workspace_id,
            "title": title,
            "content": content,
            "created_by": created_by,
            "updated_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
        _FileLock.write_json(self._wiki_file(workspace_id, page_id), data)
        return dict(data)

    async def get_wiki_page(self, page_id: str) -> dict | None:
        # Search across all workspace dirs
        wiki_base = self._base / "wiki"
        if not wiki_base.exists():
            return None
        for ws_dir in wiki_base.iterdir():
            if not ws_dir.is_dir():
                continue
            f = ws_dir / f"{page_id}.json"
            if f.exists():
                return self._load_json(f)
        return None

    async def list_wiki_pages(self, workspace_id: str) -> list[dict]:
        pages = []
        ws_dir = self._base / "wiki" / workspace_id
        if not ws_dir.exists():
            return pages
        for f in sorted(ws_dir.glob("*.json"), reverse=True):
            data = self._load_json(f)
            if data:
                pages.append(data)
        pages.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return pages

    async def update_wiki_page(self, page_id: str, **kwargs) -> dict | None:
        # Find the page across workspace dirs
        page = await self.get_wiki_page(page_id)
        if page is None:
            return None
        ws_id = page.get("workspace_id", "")
        for key, value in kwargs.items():
            page[key] = value
        page["updated_at"] = _now()
        _FileLock.write_json(self._wiki_file(ws_id, page_id), page)
        return dict(page)

    async def delete_wiki_page(self, page_id: str) -> bool:
        page = await self.get_wiki_page(page_id)
        if page is None:
            return False
        ws_id = page.get("workspace_id", "")
        f = self._wiki_file(ws_id, page_id)
        if f.exists():
            f.unlink(missing_ok=True)
            return True
        return False
```

- [ ] **Step 2: 提交**

```bash
git add app/db/compat.py
git commit -m "feat: implement wiki page CRUD in FileDataStore"
```

---

### Task 4: MySQLDataStore Wiki 实现

**Files:**
- Modify: `app/db/repository.py`

- [ ] **Step 1: 新增 WikiPage 导入**

在现有 `from app.db.models import` 的行尾添加 `WikiPage`：

现有：
```python
from app.db.models import (
    AuditLog, ChatMessage, GeneratedPRD,
    RequirementProfile, Session, User, Workspace,
)
```

改为：
```python
from app.db.models import (
    AuditLog, ChatMessage, GeneratedPRD,
    RequirementProfile, Session, User, WikiPage, Workspace,
)
```

- [ ] **Step 2: 在 `# ── Workspaces ──` 区域之后、Audit 之前插入 Wiki 方法**

```python
    # ── Wiki Pages ──

    async def create_wiki_page(
        self,
        workspace_id: str,
        title: str,
        content: str = "",
        created_by: str = "",
    ) -> dict:
        async with await self._get_session() as s:
            page = WikiPage(
                workspace_id=workspace_id,
                title=title,
                content=content,
                created_by=created_by,
                updated_by=created_by,
            )
            s.add(page)
            await s.commit()
            await s.refresh(page)
            return page.to_dict()

    async def get_wiki_page(self, page_id: str) -> dict | None:
        async with await self._get_session() as s:
            r = await s.execute(select(WikiPage).where(WikiPage.id == page_id))
            page = r.scalar_one_or_none()
            return page.to_dict() if page else None

    async def list_wiki_pages(self, workspace_id: str) -> list[dict]:
        async with await self._get_session() as s:
            r = await s.execute(
                select(WikiPage)
                .where(WikiPage.workspace_id == workspace_id)
                .order_by(WikiPage.updated_at.desc())
            )
            return [p.to_dict() for p in r.scalars().all()]

    async def update_wiki_page(self, page_id: str, **kwargs) -> dict | None:
        async with await self._get_session() as s:
            r = await s.execute(select(WikiPage).where(WikiPage.id == page_id))
            page = r.scalar_one_or_none()
            if page is None:
                return None
            for key, value in kwargs.items():
                if hasattr(page, key):
                    setattr(page, key, value)
            page.updated_at = datetime.now(timezone.utc)
            await s.commit()
            await s.refresh(page)
            return page.to_dict()

    async def delete_wiki_page(self, page_id: str) -> bool:
        async with await self._get_session() as s:
            r = await s.execute(select(WikiPage).where(WikiPage.id == page_id))
            page = r.scalar_one_or_none()
            if page is None:
                return False
            await s.delete(page)
            await s.commit()
            return True
```

- [ ] **Step 3: 提交**

```bash
git add app/db/repository.py
git commit -m "feat: implement wiki page CRUD in MySQLDataStore"
```

---

### Task 5: Wiki API 路由

**Files:**
- Create: `app/api/wiki.py`

- [ ] **Step 1: 创建 `app/api/wiki.py`**

```python
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
```

- [ ] **Step 2: 在 app/main.py 注册路由**

在第 168 行后添加：

```python
from app.api.wiki import router as wiki_router
app.include_router(wiki_router, prefix="/api", tags=["Wiki"])
```

- [ ] **Step 3: 提交**

```bash
git add app/api/wiki.py app/main.py
git commit -m "feat: add wiki CRUD API routes and register in main"
```

---

### Task 6: 前端 API 客户端

**Files:**
- Create: `reqcollect-web/src/api/wiki.ts`

- [ ] **Step 1: 创建 `reqcollect-web/src/api/wiki.ts`**

```typescript
/* ── Wiki Page API ── */

import { apiGet, apiPost, apiPatch, apiDelete } from './client'

export interface WikiPage {
  id: string
  workspace_id: string
  title: string
  content: string
  created_by: string
  updated_by: string
  created_at: string
  updated_at: string
}

export async function fetchWikiPages(workspaceId: string): Promise<WikiPage[]> {
  const res: any = await apiGet(`/wiki?workspace_id=${encodeURIComponent(workspaceId)}`)
  return res.pages || []
}

export async function fetchWikiPage(pageId: string): Promise<WikiPage> {
  const res: any = await apiGet(`/wiki/${encodeURIComponent(pageId)}`)
  return res.page
}

export async function createWikiPage(data: { workspace_id: string; title: string; content?: string }): Promise<WikiPage> {
  const res: any = await apiPost('/wiki', data)
  return res.page
}

export async function updateWikiPage(pageId: string, data: { title?: string; content?: string }): Promise<WikiPage> {
  const res: any = await apiPatch(`/wiki/${encodeURIComponent(pageId)}`, data)
  return res.page
}

export async function deleteWikiPage(pageId: string): Promise<void> {
  await apiDelete(`/wiki/${encodeURIComponent(pageId)}`)
}
```

- [ ] **Step 2: 提交**

```bash
git add reqcollect-web/src/api/wiki.ts
git commit -m "feat: add wiki API client"
```

---

### Task 7: 前端路由

**Files:**
- Modify: `reqcollect-web/src/router/index.ts`

- [ ] **Step 1: 在 Chat 路由之后新增 Wiki 路由**

```typescript
    {
      path: '/workspace/:id/wiki/new',
      name: 'WikiNew',
      component: () => import('@/views/wiki/WikiPageEditor.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspace/:id/wiki/:pageId',
      name: 'WikiView',
      component: () => import('@/views/wiki/WikiPageView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspace/:id/wiki/:pageId/edit',
      name: 'WikiEdit',
      component: () => import('@/views/wiki/WikiPageEditor.vue'),
      meta: { requiresAuth: true },
    },
```

- [ ] **Step 2: 提交**

```bash
git add reqcollect-web/src/router/index.ts
git commit -m "feat: add wiki page routes"
```

---

### Task 8: WikiPageView.vue — Markdown 阅读页

**Files:**
- Create: `reqcollect-web/src/views/wiki/WikiPageView.vue`
- Note: also create `reqcollect-web/src/views/wiki/` directory

- [ ] **Step 1: 创建目录和文件**

```bash
mkdir -p reqcollect-web/src/views/wiki
```

```vue
<template>
  <AppLayout>
    <div class="wiki-view-page">
      <!-- Top bar -->
      <div class="wiki-topbar">
        <el-button text size="small" @click="goBack">← 返回文库</el-button>
        <div class="wiki-topbar-right">
          <el-button size="small" @click="goEdit" v-if="page">编辑</el-button>
          <el-popconfirm
            v-if="page"
            title="确定删除此页面？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            @confirm="handleDelete"
          >
            <template #reference>
              <el-button size="small" type="danger" text>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" v-loading="loading" style="height:200px" />

      <!-- Error -->
      <el-result v-else-if="error" icon="error" :title="error" />

      <!-- Content -->
      <div v-else-if="page" class="wiki-content">
        <h1 class="wiki-title">{{ page.title }}</h1>
        <div class="wiki-meta">
          <span>最后更新: {{ formatDate(page.updated_at) }}</span>
          <span v-if="page.updated_by"> · 编辑者: {{ page.updated_by }}</span>
        </div>
        <el-divider />
        <div class="wiki-body markdown-body" v-html="renderedContent" />
      </div>

      <el-empty v-else description="页面不存在" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { fetchWikiPage, deleteWikiPage } from '@/api/wiki'
import type { WikiPage } from '@/api/wiki'
import AppLayout from '@/components/layout/AppLayout.vue'

const route = useRoute()
const router = useRouter()
const page = ref<WikiPage | null>(null)
const loading = ref(true)
const error = ref('')

const renderedContent = computed(() => {
  if (!page.value) return ''
  try {
    return marked(page.value.content || '')
  } catch {
    return page.value.content || ''
  }
})

function formatDate(d: string) {
  if (!d) return ''
  try { return new Date(d).toLocaleString('zh-CN') } catch { return '' }
}

function goBack() {
  const wsId = route.params.id
  router.push(`/workspace/${wsId}`)
}

function goEdit() {
  const wsId = route.params.id
  const pageId = route.params.pageId
  router.push(`/workspace/${wsId}/wiki/${pageId}/edit`)
}

async function handleDelete() {
  try {
    await deleteWikiPage(route.params.pageId as string)
    ElMessage.success('已删除')
    goBack()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    page.value = await fetchWikiPage(route.params.pageId as string)
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.wiki-view-page {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.wiki-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.wiki-topbar-right {
  display: flex;
  gap: 8px;
}

.wiki-title {
  font-size: 28px;
  font-weight: 700;
  color: #1d2129;
  margin: 0 0 8px;
}

.wiki-meta {
  font-size: 13px;
  color: #86909c;
}

.wiki-body {
  line-height: 1.8;
  font-size: 15px;
  color: #1d2129;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add reqcollect-web/src/views/wiki/WikiPageView.vue
git commit -m "feat: add WikiPageView component with Markdown rendering"
```

---

### Task 9: WikiPageEditor.vue — 分栏编辑器

**Files:**
- Create: `reqcollect-web/src/views/wiki/WikiPageEditor.vue`

- [ ] **Step 1: 创建文件**

```vue
<template>
  <AppLayout>
    <div class="wiki-editor-page">
      <!-- Top bar -->
      <div class="editor-topbar">
        <el-button text size="small" @click="handleCancel">← 返回</el-button>
        <div class="editor-topbar-right">
          <span class="editor-mode">{{ isNew ? '新建页面' : '编辑页面' }}</span>
          <el-button type="primary" size="small" :loading="saving" @click="handleSave">
            {{ isNew ? '创建' : '保存' }}
          </el-button>
        </div>
      </div>

      <!-- Editor body -->
      <div class="editor-body" v-if="loaded">
        <div class="editor-left">
          <el-input
            v-model="form.title"
            placeholder="页面标题"
            class="title-input"
            size="large"
          />
          <textarea
            v-model="form.content"
            class="editor-textarea"
            placeholder="在此编写 Markdown 内容..."
          />
        </div>
        <div class="editor-divider"></div>
        <div class="editor-right">
          <div class="preview-header">预览</div>
          <div class="preview-body markdown-body" v-html="renderedContent" />
        </div>
      </div>

      <div v-else v-loading="true" style="height:300px" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { fetchWikiPage, createWikiPage, updateWikiPage } from '@/api/wiki'
import AppLayout from '@/components/layout/AppLayout.vue'

const route = useRoute()
const router = useRouter()

const isNew = computed(() => !route.params.pageId || route.params.pageId === 'new')
const workspaceId = computed(() => route.params.id as string)
const pageId = computed(() => route.params.pageId as string)

const loaded = ref(false)
const saving = ref(false)
const form = reactive({ title: '', content: '' })

const renderedContent = computed(() => {
  try {
    return marked(form.content || '')
  } catch {
    return form.content || ''
  }
})

function handleCancel() {
  if (isNew.value) {
    router.push(`/workspace/${workspaceId.value}`)
  } else {
    router.push(`/workspace/${workspaceId.value}/wiki/${pageId.value}`)
  }
}

async function handleSave() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  saving.value = true
  try {
    if (isNew.value) {
      const page = await createWikiPage({
        workspace_id: workspaceId.value,
        title: form.title.trim(),
        content: form.content,
      })
      ElMessage.success('创建成功')
      router.push(`/workspace/${workspaceId.value}/wiki/${page.id}`)
    } else {
      await updateWikiPage(pageId.value, {
        title: form.title.trim(),
        content: form.content,
      })
      ElMessage.success('已保存')
      router.push(`/workspace/${workspaceId.value}/wiki/${pageId.value}`)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!isNew.value) {
    try {
      const page = await fetchWikiPage(pageId.value)
      form.title = page.title
      form.content = page.content
    } catch {
      ElMessage.error('加载页面失败')
    }
  }
  loaded.value = true
})
</script>

<style scoped>
.wiki-editor-page {
  height: calc(100vh - var(--topbar-height, 0px));
  display: flex;
  flex-direction: column;
}

.editor-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.editor-topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-mode {
  font-size: 13px;
  color: #86909c;
}

.editor-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  overflow-y: auto;
}

.editor-divider {
  width: 1px;
  background: #ebeef5;
  flex-shrink: 0;
}

.editor-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  overflow-y: auto;
  background: #fafafa;
}

.title-input {
  margin-bottom: 12px;
}

.title-input :deep(.el-input__inner) {
  font-size: 20px;
  font-weight: 600;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 12px;
  font-size: 14px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  line-height: 1.6;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.editor-textarea:focus {
  border-color: #409eff;
}

.preview-header {
  font-size: 13px;
  font-weight: 500;
  color: #86909c;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.preview-body {
  line-height: 1.8;
  font-size: 15px;
}

@media (max-width: 768px) {
  .editor-body {
    flex-direction: column;
  }
  .editor-divider {
    display: none;
  }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add reqcollect-web/src/views/wiki/WikiPageEditor.vue
git commit -m "feat: add WikiPageEditor component with split-pane Markdown editor"
```

---

### Task 10: WorkspaceDetail.vue — Wiki tab

**Files:**
- Modify: `reqcollect-web/src/views/WorkspaceDetail.vue`

- [ ] **Step 1: 新增 Wiki 相关导入和状态**

在 script 的 import 区域添加：
```typescript
import { fetchWikiPages } from '@/api/wiki'
import type { WikiPage } from '@/api/wiki'
```

在现有状态声明后新增：
```typescript
const wikiPages = ref<WikiPage[]>([])
const loadingWiki = ref(false)
```

在 `load` 函数中、加载 sessions 的代码之后添加 wiki 加载逻辑（或在 Wiki tab 被激活时懒加载）：

```typescript
async function loadWiki() {
  const id = route.params.id as string
  loadingWiki.value = true
  try {
    wikiPages.value = await fetchWikiPages(id)
  } catch {}
  finally { loadingWiki.value = false }
}

// 监听 tab 切换，切换到 wiki 时才加载
watch(activeTab, (tab) => {
  if (tab === 'wiki' && wikiPages.value.length === 0) {
    loadWiki()
  }
})
```

- [ ] **Step 2: Template 中新增 Wiki tab**

在 `el-tabs` 的最后一个 `el-tab-pane` 之后添加：

```vue
        <el-tab-pane label="Wiki 文库" name="wiki">
          <div v-if="!workspace" v-loading="true" style="height:200px" />
          <div v-else class="wiki-section">
            <div class="section-actions">
              <span class="section-count">共 {{ wikiPages.length }} 个页面</span>
              <el-button size="small" type="primary" @click="goNewWiki">+ 新建页面</el-button>
            </div>
            <el-table :data="wikiPages" v-loading="loadingWiki" stripe style="width:100%" empty-text="暂无 Wiki 页面">
              <el-table-column prop="title" label="页面标题" min-width="240" />
              <el-table-column label="最后编辑" width="180">
                <template #default="{ row }">
                  <span>{{ formatDate(row.updated_at) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button size="small" text type="primary" @click="goWikiView(row.id)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
```

- [ ] **Step 3: 新增方法**

```typescript
function goNewWiki() {
  const wsId = route.params.id as string
  router.push(`/workspace/${wsId}/wiki/new`)
}

function goWikiView(pageId: string) {
  const wsId = route.params.id as string
  router.push(`/workspace/${wsId}/wiki/${pageId}`)
}
```

- [ ] **Step 4: 更新 template 中的 import**

在 Vite + Vue3 中 `marked` 需要被导入，确认项目中已有 `marked.js` 通过 CDN 或 npm 引入。
检查 `reqcollect-web/package.json`：
```bash
grep marked reqcollect-web/package.json
```

如果 marked 不在 package.json 中，安装：
```bash
cd reqcollect-web && npm install marked
```

- [ ] **Step 5: 提交**

```bash
git add reqcollect-web/src/views/WorkspaceDetail.vue
git commit -m "feat: add Wiki tab to WorkspaceDetail page"
```

---

### Task 11: 前端构建 + 验证

**Files:**
- Modify: whole `reqcollect-web/`

- [ ] **Step 1: 检查 marked 是否已安装**

```bash
grep -c '"marked"' reqcollect-web/package.json
```

如果返回 0，安装：
```bash
cd reqcollect-web && npm install marked
```

- [ ] **Step 2: TypeScript 检查**

```bash
cd reqcollect-web && npx vue-tsc --noEmit 2>&1
```

- [ ] **Step 3: 构建**

```bash
cd reqcollect-web && npm run build 2>&1
```

- [ ] **Step 4: 集成验证**

确认以下流程可工作：
1. 登录 → 进入工作空间详情 → 看到「Wiki 文库」tab
2. 点击「+ 新建页面」→ 进入编辑器
3. 输入标题和 Markdown 内容 → 实时预览
4. 点击创建 → 跳转到阅读页 → Markdown 正确渲染
5. 点击「编辑」→ 加载已有内容 → 修改后保存
6. 阅读页点击「删除」→ popconfirm → 确认后删除 → 返回列表
7. 页面列表显示标题、更新时间

- [ ] **Step 5: 提交**

```bash
git add -A && git commit -m "feat: wiki page basic CRUD with Markdown editor
- DataStore protocol, FileDataStore, MySQLDataStore wiki CRUD
- WikiPage ORM model + idempotent migration
- API: GET/POST/PATCH/DELETE /api/wiki
- Frontend: WikiPageView, WikiPageEditor, WorkspaceDetail wiki tab
- Split-pane Markdown editor with live preview"
```
