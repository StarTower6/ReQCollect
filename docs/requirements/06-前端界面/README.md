# 06 — 前端界面升级

## 概述

当前为单页原生 HTML/CSS/JS 前端（`static/index.html`，1828 行）。
升级为 **Vue 3 项目级架构**（Vite + Element Plus + Vue Router），
独立目录开发，保留现有全部 CSS 设计变量和配色体系。

## 当前状态 ✅ 已实现

### 核心功能
- [x] 对话消息区（用户气泡+AI气泡，Markdown 渲染）
- [x] SSE 流式实时输出
- [x] 左侧会话列表
- [x] 新建/切换/删除会话
- [x] 快捷回复按钮（ready_to_generate、awaiting_approval）
- [x] 输入框 + Enter 发送

### 界面设计
- [x] 完整的 CSS 设计系统（变量、配色、间距、阴影）
- [x] 自适应气泡样式（用户蓝右、AI 白左）
- [x] 滚动条美化
- [x] 响应式：900px 以下隐藏侧边栏

### 交互
- [x] 自动滚动到底部
- [x] 输入框自动高度
- [x] 会话列表选中状态

## 待实现 🔲

### 项目架构

```
reqcollect-web/                    ← 独立前端项目目录
├── index.html                     ← 入口 HTML
├── vite.config.ts                 ← Vite 配置（proxy API 到 :9900）
├── package.json
├── src/
│   ├── main.ts                    ← 应用入口
│   ├── App.vue                    ← 根组件
│   ├── assets/
│   │   └── styles/
│   │       ├── variables.css      ← 现有 CSS 设计系统变量（完整保留）
│   │       ├── chat-bubbles.css   ← 对话气泡样式
│   │       └── layout.css         ← 三栏布局样式
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.vue      ← 三栏布局容器
│   │   │   ├── TopBar.vue         ← 顶部导航栏
│   │   │   └── SideBar.vue        ← 左侧会话列表
│   │   ├── chat/
│   │   │   ├── ChatArea.vue       ← 中间对话区
│   │   │   ├── MessageBubble.vue  ← 单条消息（头像+气泡+时间戳）
│   │   │   ├── MessageList.vue    ← 消息列表 + 自动滚动
│   │   │   ├── QuickReplyBar.vue  ← 快捷回复按钮组
│   │   │   └── ChatInput.vue      ← 输入框 + 发送
│   │   ├── profile/
│   │   │   ├── ProfilePanel.vue   ← 右侧需求画像面板
│   │   │   ├── SufficiencyRing.vue ← 完整度进度环
│   │   │   └── FieldStatusList.vue ← 字段状态列表
│   │   └── prd/
│   │       ├── PrdPreview.vue     ← PRD 预览页
│   │       └── PrdToc.vue         ← PRD 目录导航
│   ├── views/
│   │   ├── ChatView.vue           ← 主对话页
│   │   ├── PrdView.vue            ← PRD 预览页（独立路由）
│   │   └── DashboardView.vue      ← 仪表盘（P2）
│   ├── router/
│   │   └── index.ts               ← 路由定义
│   ├── stores/
│   │   ├── chat.ts                ← 对话状态（消息列表、流式）
│   │   ├── session.ts             ← 会话列表状态
│   │   ├── profile.ts             ← 需求画像状态
│   │   └── prd.ts                 ← PRD 状态
│   └── api/
│       ├── client.ts              ← axios/fetch 封装
│       ├── session.ts             ← 会话 API
│       ├── chat.ts                ← 对话 API（SSE）
│       ├── profile.ts             ← 画像 API
│       └── prd.ts                 ← PRD API
```

### P0 — 三栏布局
- [ ] **Vite + Vue 3 项目** — `reqcollect-web/` 独立前端目录
- [ ] **Element Plus** — 成熟中文企业 UI 组件库
- [ ] **Vue Router** — `/chat` `/prd/:id` 路由支持
- [ ] **Pinia** — 全局状态管理（会话/消息/画像/PRD）
- [ ] **三栏布局**
  ```
  ┌──────────┬──────────────────────┬──────────────┐
  │ 会话列表  │      对话区          │  需求画像     │
  │ 搜索栏   │    消息气泡          │  完整度进度条  │
  │ 列表     │    Markdown 渲染     │  字段状态     │
  │ ＋新建   │    快捷回复          │  折叠面板     │
  │          │    输入框            │              │
  └──────────┴──────────────────────┴──────────────┘
  ```
- [ ] **响应式** — 大屏固定三栏(左≤260px/中自适应/右≤320px)；1200px以下右侧折叠为抽屉按钮
- [ ] **设计约束** — 完整保留现有 CSS 变量体系，不替换任何配色/间距/阴影

### P0 — 需求画像面板
- [ ] 完整度进度环（实时更新）
- [ ] 11 字段按权重排序显示：绿色圆点=已填，灰色=待填
- [ ] 点击已填字段展开详情
- [ ] 最左侧显示缺失字段引导提示

### P1 — 对话增强
- [ ] 消息头像 — 用户/AI 分别显示头像
- [ ] 消息时间戳 — 每条消息显示时间
- [ ] 代码高亮 — highlight.js 集成
- [ ] 消息复制 — 悬停显示复制按钮
- [ ] 流式打字效果 — 逐词出现的动画效果

### P1 — PRD 预览页
- [ ] **PRD 独立页面** — `/prd/:id` 路由，左侧目录导航 + 章节定位
- [ ] **下载按钮** — 下载 Markdown/Word/PDF
- [ ] **导出进度** — 导出时显示进度条

### P2（后期迭代）
- [ ] 暗色模式
- [ ] 仪表盘与需求看板
- [ ] 消息搜索与日期分组

## 验收标准

### P0 布局
- [ ] 三栏布局正常显示，切换会话时右侧画像内容同步更新
- [ ] 窗口 <1200px 时右侧面板折叠为抽屉按钮
- [ ] 所有现有对话功能不受影响（发送/流式/快捷回复）

### P0 画像
- [ ] 完整度进度环实时更新
- [ ] 11 字段按权重排序，已填/待填状态区分
- [ ] 点击已填字段显示详情
- [ ] 缺失字段引导提示

### P1 对话增强
- [ ] 消息显示头像和时间戳
- [ ] 代码块语法高亮
- [ ] 消息复制按钮

## 技术约束
- ❌ 不替换现有 CSS 设计系统
- Vue 3 + Vite + TypeScript（推荐，不强制）
- Element Plus 组件库
- Vue Router 路由
- Pinia 状态管理
- 生产构建输出到 `reqcollect-web/dist/`，由 Nginx 或 FastAPI 静态文件服务承载
