# Report: Wiki 详情页 UI 改进

## 验收标准验证
- [x] **P0**: Wiki 页显示创建者/编辑者的显示名称而非数字 ID → OK
- [x] **P0**: 代码块有语法高亮 (highlight.js) → OK
- [x] **P0**: Mermaid 图表正常渲染 → OK
- [x] **P1**: 显示创建时间 → OK
- [x] **P1**: 长内容有滚动条 → OK (overflow-y: auto; height: 100%)
- [x] **P0**: 构建通过 → OK

## 功能验证
- [x] API `/api/wiki/{page_id}` 返回 `created_by_name` + `updated_by_name` → OK ("Admin")
- [x] WikiPageView 导入 `hljs` + `mermaid` → OK
- [x] WikiPageView `afterRender()` 执行代码高亮 + Mermaid → OK
- [x] 前端构建无 TypeScript 错误 → OK
- [x] Docker 构建部署成功 → OK

## 回归检查
- [x] `/api/health` 返回 200 → OK
- [x] existing wiki 页面加载正常 → OK
- [x] 依赖没有冲突 → OK

## 评估结论
✅ **通过**

## 改动内容

### 后端 (`app/api/wiki.py`)
- `wiki_get()` 端点增加 `get_user_by_id()` 调用，解析 `created_by` / `updated_by` 为 `display_name`
- 当 `created_by == updated_by` 时复用同一名称，避免重复查库

### 前端 (`reqcollect-web/src/views/wiki/WikiPageView.vue`)
- 增加 `hljs` 和 `mermaid` 导入 + `mermaid.initialize()`
- 增加 `afterRender()` 异步函数：代码高亮 (hljs) + Mermaid 图渲染
- `renderedContent` computed 增加 `async: false` 和同步/异步双路径（同 PrdView 模式）
- 分解 `renderWikilinks()` 工具函数以复用
- 元信息显示创建时间 + 创建者名称 + 最后编辑时间 + 编辑者名称
- 容器增加 `overflow-y: auto; height: 100%` 以支持滚动

### 类型 (`reqcollect-web/src/api/wiki.ts`)
- `WikiPage` 接口增加 `created_by_name?` 和 `updated_by_name?` 可选字段
