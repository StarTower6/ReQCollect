# Report: 13 — 工作空间（P0 核心 MVP）

## 验收标准验证
- [x] P0: 创建工作空间（名称必填） → **OK** ✅
- [x] P0: 工作空间列表页展示所有空间 → **OK** ✅
- [x] P0: 工作空间详情页（概览 + 会话列表） → **OK** ✅
- [x] P0: 会话创建时选择所属工作空间 → **OK** ✅（workspace_id 字段）
- [x] P0: 工作空间内仅显示本空间会话 → **OK** ✅（GET /api/workspaces/{id}/sessions）
- [x] P0: 现有 session 的 project_name 自动迁移为工作空间 → **OK** ✅
- [x] P1: 编辑/删除工作空间 → **OK** ✅

## 改动清单

### 新增文件（5 个）
| 文件 | 说明 |
|------|------|
| `app/db/models.py` | Workspace ORM 模型 |
| `app/api/workspace.py` | 7 个 API 端点 |
| `app/core/workspace.py` | 数据迁移工具 |
| `reqcollect-web/src/views/WorkspaceList.vue` | 工作空间列表页 |
| `reqcollect-web/src/views/WorkspaceDetail.vue` | 工作空间详情页 |
| `reqcollect-web/src/api/workspace.ts` | 前端 API 客户端 |

### 修改文件（8 个）
| 文件 | 说明 |
|------|------|
| `app/db/__init__.py` | Workspace CRUD 抽象方法 |
| `app/db/compat.py` | FileDataStore Workspace 实现 |
| `app/db/repository.py` | MySQLDataStore Workspace 实现 |
| `app/main.py` | 注册 workspace 路由 + 启动迁移 |
| `app/services/pm_agent_service.py` | create_session 传 workspace_id |
| `reqcollect-web/src/router/index.ts` | 新增 workspace 路由 + 根路径改 /workspaces |
| `reqcollect-web/src/components/layout/SideBar.vue` | 新增「工作空间」导航入口 |
| `reqcollect-web/src/views/LoginView.vue` | 登录后跳转到 /workspaces |

## API 端点
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/workspaces | 创建工作空间 |
| GET | /api/workspaces | 列表 |
| GET | /api/workspaces/{id} | 详情 |
| PATCH | /api/workspaces/{id} | 编辑 |
| DELETE | /api/workspaces/{id} | 删除 |
| GET | /api/workspaces/{id}/sessions | 空间内会话 |

## 未做（P1 批次）
- 工作空间成员管理（第 4 章）
- Wiki 文库（第 3 章）
- 需求图谱（第 5 章）
- 角色权限校验

## 评估结论
✅ **通过**
