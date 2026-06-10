# Wiki 页面功能（基础版）— 设计文档

## 1. 概述

在工作空间内提供 Wiki 文库功能：用户可以创建、查看、编辑、删除 Wiki 页面，
使用 Markdown 编写，实时预览渲染效果。

实现范围：基础版（Wiki 页面 CRUD + Markdown 编辑器 + 工作空间级页面列表）。

## 2. 数据模型

### 2.1 MySQL ORM — WikiPage

```python
class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 迁移：CREATE TABLE wiki_pages (...)
```

### 2.2 FileDataStore

目录结构：`pm_data/wiki/{workspace_id}/{page_id}.json`

### 2.3 DataStore 协议扩展

```python
@abstractmethod
async def create_wiki_page(self, workspace_id: str, title: str, content: str, created_by: str) -> dict

@abstractmethod
async def get_wiki_page(self, page_id: str) -> dict | None

@abstractmethod
async def list_wiki_pages(self, workspace_id: str) -> list[dict]

@abstractmethod
async def update_wiki_page(self, page_id: str, **kwargs) -> dict | None

@abstractmethod
async def delete_wiki_page(self, page_id: str) -> bool
```

### 2.4 MySQL 迁移

在 `app/db/database.py` 的 `init_db` 中新增 DDL 迁移。

## 3. API

### 3.1 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/wiki?workspace_id=xxx` | 列出工作空间下所有 wiki 页面 |
| POST | `/api/wiki` | 创建 wiki 页面 |
| GET | `/api/wiki/{page_id}` | 获取单页详情 |
| PATCH | `/api/wiki/{page_id}` | 更新页面内容/标题 |
| DELETE | `/api/wiki/{page_id}` | 删除页面 |

### 3.2 请求/响应模型

```python
class WikiPageCreate(BaseModel):
    workspace_id: str
    title: str
    content: str = ""

class WikiPageUpdate(BaseModel):
    title: str = ""
    content: str = ""
```

所有路由需要 `get_current_user` 依赖注入。

### 3.3 文件

新增 `app/api/wiki.py`，在 `app/main.py` 中注册路由：
```python
from app.api.wiki import router as wiki_router
app.include_router(wiki_router, prefix="/api", tags=["Wiki"])
```

## 4. 前端

### 4.1 路由

| 路径 | 组件 | 说明 |
|------|------|------|
| `/workspace/:id/wiki/:pageId` | `WikiPageView.vue` | 查看 wiki 页 |
| `/workspace/:id/wiki/:pageId/edit` | `WikiPageEditor.vue` | 编辑 wiki 页 |
| `/workspace/:id/wiki/new` | `WikiPageEditor.vue` | 新建 wiki 页 |

### 4.2 WorkspaceDetail.vue — 新增 Wiki tab

在 `el-tabs` 中新增 `el-tab-pane`：
```vue
<el-tab-pane label="Wiki 文库" name="wiki">
  <WikiList :workspace-id="id" />
</el-tab-pane>
```

WikiList 展示：
- 页面列表（标题、最后编辑者、更新时间）
- 「+ 新建页面」按钮 → 跳转到 `/workspace/:id/wiki/new`
- 点击页面行 → 跳转到 `/workspace/:id/wiki/:pageId`

### 4.3 WikiPageView.vue

布局：
- 顶部：标题 + 操作按钮（编辑、返回）
- 内容区：渲染 Markdown（使用 marked.js，项目已有）

### 4.4 WikiPageEditor.vue

- URL 参数决定新建/编辑模式（`:pageId` 存在为编辑）
- 分栏布局（flex）：左侧编辑区 / 右侧预览区
- 编辑区：标题 input + Markdown textarea
- 预览区：marked.js 实时渲染

### 4.5 前端 API 客户端

新增 `reqcollect-web/src/api/wiki.ts`

## 5. 验收标准

- [ ] P0: wiki_pages 表/文件存储创建，DataStore 协议扩展完成
- [ ] P0: API CRUD 端点全部实现，返回正确状态码
- [ ] P0: WorkspaceDetail 显示「Wiki 文库」tab，列出页面列表
- [ ] P0: 新建 Wiki 页面：弹窗填标题 → 进入编辑器 → 保存
- [ ] P0: 编辑 Wiki 页面：分栏编辑器 + Markdown 实时预览
- [ ] P0: 查看 Wiki 页面：渲染 Markdown，显示标题和元信息
- [ ] P0: 删除 Wiki 页面：popconfirm 确认
- [ ] P1: 页面列表显示最后编辑者、更新时间
- [ ] P1: MySQL 迁移自动执行（无感降级到文件存储）

## 6. 不做

- 不实现 `[[链接]]` 解析（P1）
- 不实现版本历史（P1）
- 不实现图谱（P1）
- 不实现 AI 自动创建/补充（P1）
- 不实现页面层级树（parent_id）
