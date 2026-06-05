# Plan: 06 — 前端界面升级 (Vite + Vue 3 项目)

## 1. 任务理解

- **需求来源**: `docs/requirements/06-前端界面/README.md`
- **核心目标**: 将当前 1356 行单 HTML CDN 前端，升级为 **Vite + Vue 3 + TypeScript 项目级架构**，独立目录 `reqcollect-web/`
- **用户选择**: 完整实现（P0 三栏布局+画像 + P1 对话增强+PRD预览 + P2 仪表盘）

## 2. 架构图

```
Dev 模式:                              Production 模式:
┌──────────────────┐                    ┌──────────────────┐
│ Vite Dev Server  │                    │  FastAPI :9900   │
│ localhost:5173   │                    │  ┌────────────┐  │
│ proxy /api → :9900│                    │  │ static/    │  │
└────────┬─────────┘                    │  │   index.html│  │
         │                              │  ├────────────┤  │
         │ proxy /api                   │  │ reqcollect- │  │
         ▼                              │  │  web/dist/  │  │
┌──────────────────┐                    │  │   (Vue SPA) │  │
│ FastAPI :9900    │                    └──┴────────────┴──┘
│ /api/pm/*        │
└──────────────────┘
```

## 3. 目录结构

```
reqcollect-web/
├── index.html                 ← 入口 HTML
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts             ← proxy /api → :9900
├── src/
│   ├── main.ts                ← 应用入口 (createApp + router + pinia)
│   ├── App.vue                ← 根组件 (router-view)
│   ├── env.d.ts               ← TypeScript 声明
│   ├── assets/
│   │   └── styles/
│   │       ├── variables.css  ← 现有 CSS 设计系统变量（完整保留）
│   │       └── global.css     ← 全局样式 + 气泡 + 布局
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.vue  ← 三栏布局容器
│   │   │   ├── TopBar.vue     ← 顶部导航栏
│   │   │   └── SideBar.vue    ← 左侧会话列表
│   │   ├── chat/
│   │   │   ├── ChatArea.vue   ← 中间对话区
│   │   │   ├── MessageBubble.vue  ← 单条消息
│   │   │   ├── MessageList.vue    ← 消息列表
│   │   │   ├── QuickReplyBar.vue  ← 快捷回复
│   │   │   └── ChatInput.vue      ← 输入框
│   │   ├── profile/
│   │   │   ├── ProfilePanel.vue   ← 右侧画像面板
│   │   │   ├── SufficiencyRing.vue ← 进度环
│   │   │   └── FieldStatusList.vue ← 字段列表
│   │   └── prd/
│   │       ├── PrdPreview.vue     ← PRD 预览
│   │       └── PrdToc.vue         ← PRD 目录
│   ├── views/
│   │   ├── ChatView.vue       ← 主对话页
│   │   ├── PrdView.vue        ← PRD 预览页
│   │   └── DashboardView.vue  ← 仪表盘
│   ├── router/
│   │   └── index.ts           ← /chat /prd/:id /dashboard
│   ├── stores/
│   │   ├── chat.ts            ← 消息列表、SSE 流式
│   │   ├── session.ts         ← 会话列表、CRUD
│   │   ├── profile.ts         ← 需求画像
│   │   └── prd.ts             ← PRD
│   ├── api/
│   │   ├── client.ts          ← fetch 封装
│   │   ├── session.ts         ← 会话 API
│   │   ├── chat.ts            ← SSE 对话
│   │   ├── profile.ts         ← 画像 API
│   │   └── prd.ts             ← PRD API
│   └── types/
│       └── index.ts           ← 类型定义
```

## 4. 验收标准

### P0 — 布局
- [ ] P0: `npm run dev` 启动 Vite 开发服务器，页面正常渲染
- [ ] P0: 三栏布局正常显示（左≤260px/中自适应/右≤320px）
- [ ] P0: 窗口 <1200px 右侧折叠为抽屉
- [ ] P0: 所有对话功能正常（发送/流式/快捷回复/新建/切换/删除）

### P0 — 画像
- [ ] P0: 完整度进度环实时更新
- [ ] P0: 11 字段按权重排序，已填/待填区分
- [ ] P0: 点击已填字段展开详情，缺失字段引导提示

### P1 — 对话增强
- [ ] P1: 消息头像 + 时间戳
- [ ] P1: 代码块语法高亮（highlight.js）
- [ ] P1: 悬停复制按钮

### P1 — PRD 预览
- [ ] P1: `/prd/:id` 独立页面，左侧目录导航 + 章节定位
- [ ] P1: 下载 Markdown 按钮

### P2 — 仪表盘
- [ ] P2: `/dashboard` 页面，展示会话数量、PRD 数量趋势
- [ ] P2: `npm run build` 产出到 `reqcollect-web/dist/`

### 技术约束
- [ ] 保留全部现有 CSS 设计系统变量
- [ ] 零构建工具引入（Vite 仅用于前端，不涉及后端构建）

## 5. 实施步骤

### Step 1: 项目初始化
- package.json, vite.config.ts, tsconfig.json
- main.ts, App.vue, env.d.ts
- 安装依赖: vue3, vue-router, pinia, element-plus, echarts, highlight.js

### Step 2: CSS 设计系统 + 类型定义
- variables.css (完整保留 25 个 token)
- global.css (布局、气泡、滚动条)
- types/index.ts (Session, Message, Profile, PRD)

### Step 3: API 层 + Pinia Stores
- api/client.ts (fetch 封装)
- api/session.ts, chat.ts, profile.ts, prd.ts
- stores/session.ts, chat.ts, profile.ts, prd.ts

### Step 4: 路由 + 布局组件
- router/index.ts
- components/layout/AppLayout.vue, TopBar.vue, SideBar.vue

### Step 5: 对话区组件
- ChatView.vue (组合所有 chat 子组件)
- ChatArea.vue, MessageList.vue, MessageBubble.vue, QuickReplyBar.vue, ChatInput.vue

### Step 6: 画像面板 + PRD 预览
- ProfilePanel.vue, SufficiencyRing.vue, FieldStatusList.vue
- PrdPreview.vue, PrdToc.vue, PrdView.vue

### Step 7: 仪表盘
- DashboardView.vue (ECharts 图表)

### Step 8: FastAPI 集成
- 更新 main.py 在 production 模式下 serve `reqcollect-web/dist/`

### Step 9: Evaluate
- 验收验证
- 写 report.md

## 6. 不做（明确排除）
- ❌ 暗色模式
- ❌ 消息搜索与日期分组
- ❌ Word/PDF 下载（仅 Markdown）
- ❌ 替换现有 static/index.html（新旧共存）
