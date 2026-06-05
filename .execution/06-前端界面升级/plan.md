# Plan: 06 — 前端界面升级

## 1. 任务理解

- **需求来源**: `docs/requirements/06-前端界面/README.md`
- **核心目标**: 将 1828 行原生 JS 单页升级为 Vue 3 CDN + Element Plus CDN 组件化架构，保留全部 CSS 设计系统变量
- **技术约束**: 零构建工具，单 HTML 文件，CDN 引入

## 2. 架构设计

### 当前架构（二栏）
```
┌──────────┬──────────────────────┐
│  会话列表 │      对话区          │
│  268px   │    自适应            │
└──────────┴──────────────────────┘
```

### 目标架构（三栏）
```
┌──────────┬──────────────────────┬──────────────┐
│  会话列表 │      对话区          │  需求画像     │
│  ≤260px  │    自适应            │  ≤320px      │
│  Vue 组件│    Vue 组件          │  Vue 组件    │
└──────────┴──────────────────────┴──────────────┘
         ↓ <1200px 时右侧折叠为 el-drawer
```

### 组件树
```
<App>
  ├── <Sidebar>              — 会话列表 + 搜索 + 新建
  │     ├── BrandHeader
  │     ├── SessionSearch
  │     ├── SessionList
  │     │    └── SessionItem (×N)
  │     └── SidebarFooter
  ├── <ChatArea>            — 对话区 + 输入框
  │     ├── TopBar (标题 + 完整度标签)
  │     ├── MessageList
  │     │    ├── WelcomeScreen
  │     │    ├── MessageBubble (user)
  │     │    ├── MessageBubble (assistant, Markdown)
  │     │    ├── EventBadge
  │     │    └── QuickReplies
  │     └── Composer (输入框 + 工具栏 + 发送)
  └── <ProfilePanel>        — 需求画像面板
        ├── SufficiencyRing
        ├── FieldList
        │    └── FieldItem (×11, 可展开)
        └── MissingFieldGuide
```

## 3. CDN 依赖

```html
<!-- Vue 3 (runtime only is fine since templates are in-DOM) -->
<script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
<!-- Element Plus -->
<link href="https://unpkg.com/element-plus/dist/index.css" rel="stylesheet">
<script src="https://unpkg.com/element-plus/dist/index.full.min.js"></script>
<!-- 已有: marked.js -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<!-- 新增: highlight.js -->
<link href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
```

## 4. 改动清单

### 修改文件
| 文件 | 改动 |
|------|------|
| `static/index.html` | 全量重写为 Vue 3 组件架构（保留全部 CSS 变量和设计系统） |

### 无后端改动
所有 API 端点已在前两轮实现完毕，前端仅消费现有端点。

## 5. 验收标准

### P0 — 三栏布局
- [ ] P0: 三栏布局正常显示，切换会话时右侧画像内容同步更新
- [ ] P0: 窗口 <1200px 时右侧面板折叠为抽屉按钮
- [ ] P0: 所有现有对话功能不受影响（发送/流式/快捷回复/新建/切换/删除）

### P0 — 需求画像面板
- [ ] P0: 完整度进度环实时更新（SVG 圆环，百分比显示）
- [ ] P0: 11 字段按权重排序显示，绿色圆点=已填，灰色=待填
- [ ] P0: 点击已填字段展开详情
- [ ] P0: 缺失字段引导提示

### P1 — 对话增强
- [ ] P1: 消息显示头像（用户蓝/AI PM 图标）
- [ ] P1: 消息显示时间戳
- [ ] P1: 代码块语法高亮（highlight.js）
- [ ] P1: 消息复制按钮（悬停显示）
- [ ] P1: 流式打字效果（逐词出现动画）

### 不做（明确排除）
- ❌ 暗色模式 (P2)
- ❌ 仪表盘与需求看板 (P2)
- ❌ 消息搜索与日期分组 (P2)
- ❌ PRD 独立预览页（仅保留现有内嵌展示）
- ❌ Markdown/Word/PDF 下载

## 6. 实施策略

### 渐进式迁移方案

由于是单页 1828 行，最佳方案是**全量重写**而非增量迁移，原因：
1. Vue 3 的模板语法与原生 JS DOM 操作不兼容
2. 事件绑定方式完全不同（`onclick` vs `@click`）
3. 状态管理需要从全局变量迁移到 Vue reactive data

### 保留的资产
- 全部 CSS 变量（`:root` 中的 25 个 token）
- 全部气泡/侧栏/输入框/快捷回复样式
- 品牌 Logo 样式
- 响应式断点
- SSE 流式处理逻辑（函数式保留，接入 Vue）

## 7. 实施步骤

### Step 1: 骨架 + Vue 3 挂载
- CDN 引入 Vue 3, Element Plus, highlight.js
- 三栏 HTML 结构
- Vue app 挂载 + data 初始化

### Step 2: 会话列表组件 (Sidebar)
- SessionList 组件（v-for 渲染）
- 搜索过滤（computed）
- 新建/切换/删除/置顶

### Step 3: 对话区 + SSE 流式
- MessageList + MessageBubble 组件
- SSE 流式接入（与原有逻辑兼容）
- QuickReplies 组件化
- 打字效果

### Step 4: 需求画像面板
- SufficiencyRing 组件（SVG 圆环）
- FieldList + FieldItem 组件
- 展开/折叠详情
- 缺失引导

### Step 5: P1 增强
- 头像和时间戳
- highlight.js 代码高亮
- 复制按钮
- 打字动画

### Step 6: 响应式 + 抽屉
- <1200px 右侧 el-drawer 折叠
- el-drawer 样式覆写为设计系统

### Step 7: Evaluate
- 验收验证
- 写 report.md

## 8. 数据流

```
Vue App State:
  sessionId: string
  mode: 'one_shot' | 'incremental'
  useKnowledge: boolean
  sessions: Session[]
  messages: Message[]
  profile: Profile | null
  
  computed:
    sufficiencyPercent: number
    fields Status: {filled: boolean, weight: number}[]
    filteredSessions: Session[]
    isMobile: boolean (window width)
```

```
window resize → computed isMobile → el-drawer toggle
API /sessions → sessions[]
API /profile/{sid} → profile → fields rendered
API /history/{sid} → messages[] → rendered
SSE /agent → append to messages[] → auto-scroll
```
