# Plan: 修复工作空间页面路由不匹配问题

## 1. 任务理解

### 核心问题
路由定义和实际导航路径不匹配：
- **路由定义**：`/workspace`（不带 s）→ WorkspaceList
- **实际导航**：所有代码写的是 `router.push('/workspaces')`（带 s）
- **结果**：任何指向 `/workspaces` 的导航都匹配不上路由，被 catch-all 规则重定向到 `/chat`
- **影响范围**：登录后自动跳转工作空间列表、侧边栏"工作空间管理"按钮、"新建工作空间"按钮全部失效

### 相关路径汇总
| 路由定义 | 导航代码实际路径 | 匹配？ |
|---------|----------------|--------|
| `/workspace` | `/workspaces` | ❌ |
| `/workspace/:id` | `/workspace/${id}` | ✅ |
| `/workspace/:id/wiki/:pageId` | `/workspace/${wsId}/wiki/${pageId}` | ✅ |
| `/workspace/:id/proposals` | `/workspace/${route.params.id}/proposals` | ✅ |

只有 `/workspace` 列表页有问题，其他子路由都正确。

## 2. 改动清单

- **修改文件**: `reqcollect-web/src/router/index.ts` — 将所有路由 path 从 `/workspace` 改为 `/workspaces`

## 3. 数据模型
无变更

## 4. 验收标准
- [x] P0: 登录后自动跳转到工作空间列表页，正常渲染
- [x] P0: 侧边栏"📁"按钮点击后跳转到工作空间列表页
- [x] P0: 工作空间卡片点击能进入工作空间详情页
- [x] P1: Wiki 页面、Proposal 页面等子路径导航不受影响

## 5. 风险与依赖
- 低风险：仅修改 router 中的 path 前缀，不影响组件内部逻辑
- WorkspaceDetail 等组件使用 `route.params.id` 获取参数，不受影响
- 所有子路由路径都是 `/workspace/:id/...`，整体改前缀即可

## 6. 实施步骤
1. 修改 `router/index.ts` 中所有 `path: '/workspace'` 为 `path: '/workspaces'`
2. 验证登录后重定向到工作空间列表
3. 验证从列表进入详情页
