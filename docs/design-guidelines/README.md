# ReQCollect UI 设计规范

> 版本: v1.0
> 最后更新: 2026-06-10
> 设计方向: Warm Current — 圆润亲和的企业级 AI 对话工具

---

## 目录

1. [设计原则](#1-设计原则)
2. [设计令牌系统](#2-设计令牌系统)
3. [布局结构](#3-布局结构)
4. [组件规范](#4-组件规范)
5. [交互与动效](#5-交互与动效)
6. [色彩使用指南](#6-色彩使用指南)
7. [排版规范](#7-排版规范)
8. [图标与图片](#8-图标与图片)
9. [可访问性](#9-可访问性)

---

## 1. 设计原则

本规范遵循 **CALM** 四项核心原则：

| 原则 | 含义 | 实践 |
|------|------|------|
| **C**lear | 清晰传达信息层次 | 文字层级系统、信息密度控制 |
| **A**ffordable | 可感知的交互性 | 聚焦光晕、悬浮态、反馈动效 |
| **L**ight | 轻量不沉重 | 克制阴影、充足留白、低饱和背景 |
| **M**indful | 用心对待每个像素 | 圆角一致、对齐精准、不堆砌 |

---

## 2. 设计令牌系统

所有设计令牌定义在 `reqcollect-web/src/assets/styles/variables.css` 中。

### 2.1 色彩系统

#### 品牌色阶

```css
:root {
  --brand: #3f7df6;         /* 主品牌色 — 主按钮、链接、指示器 */
  --brand-dark: #2366dc;    /* 悬停/激活 */
  --brand-soft: #edf4ff;    /* 品牌浅色底 */
  --brand-50: #eef4ff;      /* 最浅 — hover 行/背景 */
  --brand-100: #dbe7fe;     /* 标签浅底、用户气泡底色 */
  --brand-200: #b6cefd;     /* 进度条、装饰边框 */
  --brand-400: #6b9ff8;     /* 次要按钮虚线 */
  --brand-500: #3f7df6;     /* = --brand */
  --brand-600: #2366dc;     /* = --brand-dark */
  --brand-700: #1a4da8;     /* 按下态、文字强调 */
}
```

#### 语义色

```css
:root {
  --success: #2dbf6e;         /* 成功 — 柔和不扎眼 */
  --warning: #f0a030;         /* 警告 */
  --error: #e74c4c;           /* 错误 */
  --info: #6b9ff8;            /* 信息 — 同 brand-400 */

  --success-soft: #eaf8ef;    /* 成功浅底 */
  --warning-soft: #fef5e8;    /* 警告浅底 */
  --error-soft: #fdecec;      /* 错误浅底 */
  --info-soft: #edf4ff;       /* 信息浅底 — 同 brand-soft */
}
```

#### 中性色

```css
:root {
  --bg: #f7f9fd;                 /* 主背景色 */
  --sidebar: #f2f5fb;            /* 侧栏背景 */
  --sidebar-hover: #e8eef8;      /* 侧栏悬浮 */
  --panel: #ffffff;               /* 面板/卡片背景 */
  --line: #e4e9f2;               /* 边框线（标准） */
  --line-strong: #d4deec;        /* 边框线（强调） */
  --line-light: #eef2f8;         /* 边框线（更浅） */
  --fill: #f0f4fa;               /* 通用填充色 */
  --text: #202634;                /* 主文本色 */
  --muted: #6f7d92;              /* 次要文本 */
  --muted-light: #9aa6b8;        /* 辅助文本 */
  --text-placeholder: #b0bbcc;   /* 占位符文字 */
}
```

### 2.2 圆角系统

```css
:root {
  --radius-xs: 4px;         /* 标签角标 */
  --radius-sm: 8px;         /* 输入框、搜索框 */
  --radius-md: 12px;        /* 卡片、面板、气泡 */
  --radius-lg: 16px;        /* 弹窗、大卡片、主容器 */
  --radius-xl: 20px;        /* 欢迎卡片、特殊容器 */
  --radius-full: 9999px;    /* 胶囊按钮、标签 */
}
```

> 默认情况下，卡片使用 `--radius-lg`(16px)，输入框/按钮使用 `--radius-sm`(8px)，消息气泡使用 `--radius-md`(12px)。

### 2.3 阴影系统

```css
:root {
  --shadow-sm: 0 1px 3px rgba(31, 69, 126, 0.08);        /* 轻微悬浮 */
  --shadow-md: 0 4px 12px rgba(31, 69, 126, 0.10);       /* 卡片悬浮 */
  --shadow-lg: 0 8px 28px rgba(31, 69, 126, 0.12);       /* 弹窗、下拉 */
  --shadow-xl: 0 16px 44px rgba(31, 69, 126, 0.11);      /* Modal 大遮罩 */
}
```

### 2.4 间距系统

```css
:root {
  --sp-1: 4px;
  --sp-2: 8px;
  --sp-3: 12px;
  --sp-4: 16px;
  --sp-5: 20px;
  --sp-6: 24px;
  --sp-8: 32px;
  --sp-10: 40px;
  --sp-12: 48px;
}
```

### 2.5 文字层级

```css
:root {
  --text-xs: 11px;           /* 辅助文字、时间戳 */
  --text-sm: 13px;           /* 次要文字、侧栏项 */
  --text-base: 15px;         /* 正文、消息气泡 */
  --text-lg: 17px;           /* 强调正文 */
  --text-xl: 20px;           /* 小节标题 */
  --text-2xl: 24px;          /* 页面标题 */
  --text-3xl: 28px;          /* 欢迎大标题 */

  --font-normal: 400;
  --font-medium: 520;
  --font-semibold: 640;
  --font-bold: 760;
}
```

> 比例因子 ≈ 1.25（major third）。固定 px 值，不使用 `clamp()`。

### 2.6 动效曲线

```css
:root {
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);              /* 弹出/出现（默认） */
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);          /* 展开/收起 */
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);       /* 微放大、点赞 */
  --duration-fast: 150ms;     /* hover/点击反馈 */
  --duration-normal: 250ms;   /* 过渡动画（默认） */
  --duration-slow: 400ms;     /* 面板展开/收起 */
}
```

### 2.7 Z-index 层级

```css
:root {
  --z-sidebar: 10;
  --z-topbar: 20;
  --z-profile: 30;
  --z-dropdown: 50;
  --z-sticky: 100;
  --z-modal-backdrop: 200;
  --z-modal: 210;
  --z-notification: 300;
  --z-tooltip: 400;
}
```

---

## 3. 布局结构

### 3.1 全局三栏布局

```
┌─────────────────────────────────────────────────────────┐
│  SideBar (280px)  │  Main Area (flex: 1)   │Profile 300px│
│  ┌───────────────┐│ ┌──────────────────────┐│ ┌────────┐│
│  │ Brand + 新建  ││ │  TopBar (54px)       ││ │ 画像   ││
│  │ 搜索框        ││ │  —shadow-sm 毛玻璃    ││ │ 完整度  ││
│  │ 会话树        ││ ├──────────────────────┤│ │ 环     ││
│  │ 工作空间      ││ │  ChatPanel           ││ │        ││
│  │ 未分类        ││ │  —panel              ││ │ 字段   ││
│  │               ││ │  —radius-lg          ││ │ 引导   ││
│  │               ││ │  —shadow-sm          ││ │        ││
│  ├───────────────┤│ │  centered max-820px  ││ └────────┘│
│  │ 底部导航链接  ││ └──────────────────────┘└──────────┘
└─────────────────────────────────────────────────────────┘
```

### 3.2 各区域规范

| 区域 | 宽度 | 背景 | 圆角 | 阴影 | 边框 |
|------|------|------|------|------|------|
| SideBar | 280px fixed | `--panel` | 0 | 无 | `border-right: 1px solid var(--line)` |
| TopBar | 100% | `rgba(247,249,253,0.85)` + `backdrop-filter: blur(12px)` | 0 | `--shadow-sm` 底部 | — |
| Chat Panel | min(820px, 100%) centered | `--panel` | `--radius-lg`(16px) | `--shadow-sm` | — |
| Profile Panel | 300px fixed | `--panel` | 0 | 无 | `border-left: 1px solid var(--line)` |

### 3.3 响应式断点

```css
$bp-lg: 1200px;    /* 三栏完整 */
$bp-md: 820px;     /* 隐藏侧栏 */
$bp-sm: 480px;     /* 隐藏 TopBar 文字 */
```

| 断点 | 侧栏 280px | Profile 300px | TopBar | 对话区 |
|------|-----------|---------------|--------|--------|
| **≥1200px** | 显示 | 显示 | 完整 | 居中带阴影 |
| **820–1200px** | 显示 | el-drawer | 完整 | 全宽 |
| **480–820px** | hamburger | el-drawer | 仅图标+标题 | 全宽 |
| **<480px** | 抽屉覆盖 | drawer 覆盖 | 仅标题 | 全宽 |

### 3.4 页面布局模板

**A. 对话页** — 标准三栏布局，对话区为圆角卡片容器

**B. 仪表盘/列表页** — 排除侧栏和 Profile，content-padded 模式：
```css
.page-dashboard { max-width: 1200px; margin: 0 auto; padding: var(--sp-6); }
```

**C. 详情/编辑页** — 全宽模式，无侧栏/Profile，左右分栏或全宽展示

---

## 4. 组件规范

### 4.1 消息气泡

圆润不对称圆角 + 微阴影，体现"对话质感"。

#### 用户气泡（右对齐）
```css
.msg-user {
  background: var(--brand-100);  /* #dbe7fe */
  color: var(--text);
  border-radius: var(--radius-md) var(--radius-md) var(--radius-xs) var(--radius-md);
  padding: var(--sp-3) var(--sp-4);
  box-shadow: var(--shadow-sm);
  max-width: min(680px, 88%);
}
```

#### AI 气泡（左对齐，Markdown 渲染）
```css
.msg-assistant {
  background: var(--panel);
  border-radius: var(--radius-md) var(--radius-md) var(--radius-md) var(--radius-xs);
  padding: var(--sp-3) var(--sp-4);
  box-shadow: var(--shadow-sm);
  max-width: min(680px, 88%);
}
```

| 属性 | 规范 |
|------|------|
| 头像 | 30px 圆形，用户=品牌色，AI=品牌渐变 |
| 时间戳 | 11px `--muted-light` |
| 气泡间距 | 上下 `--sp-2` |

### 4.2 输入框（ChatInput）

```
┌────────────────────────────────────────┐
│  快捷回复标签 │ 标签 │ 标签 │  [+]     │  ← radius-full
├────────────────────────────────────────┤
│ ┌──────────────────────────────────┐   │
│ │ 输入消息...                 [↑] │   │  ← radius-md
│ └──────────────────────────────────┘   │
└────────────────────────────────────────┘
```

```css
.chat-input {
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--panel);
  font-size: var(--text-base);
  max-height: 180px;
  transition: border-color var(--duration-fast) var(--ease-out),
              box-shadow var(--duration-fast) var(--ease-out);
}
.chat-input:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-soft);
}
```

| 属性 | 规范 |
|------|------|
| 圆角 | `--radius-md` (12px) |
| 聚焦效果 | blue glow ring (`box-shadow 3px`) |
| 发送按钮 | 36px 圆形 `--brand` → hover `--brand-600`, `scale(1.05)` 动效 |
| 最大高度 | 180px auto-grow |

### 4.3 按钮

默认使用 Element Plus `<el-button>`，覆盖以下样式：

| 类型 | 实现 | 背景 | 文字 | 圆角 | Hover |
|------|------|------|------|------|-------|
| Primary | `el-button--primary` | `--brand` | #fff | `--radius-sm` | `--brand-600` |
| Soft | `el-button` + class | `--brand-50` | `--brand` | `--radius-sm` | `--brand-100` |
| Outlined | `el-button--plain` | transparent | `--brand` | `--radius-sm` | bg `--brand-50` |
| Ghost | `el-button--text` | transparent | `--muted` | `--radius-sm` | bg `--fill` |
| Capsule | custom | `--brand` | #fff | `--radius-full` | `--brand-600` |
| Icon Round | custom 36px | `--brand` | #fff | 50% | `scale(1.05)` |

### 4.4 卡片

```css
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);  /* 16px */
  padding: var(--sp-5);
  transition: box-shadow var(--duration-fast) var(--ease-out),
              border-color var(--duration-fast) var(--ease-out);
}
.card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--brand-200);
}
```

- 工作空间列表：`grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))`，间距 `var(--sp-5)`

### 4.5 弹窗（Dialog）

覆盖 Element Plus `<el-dialog>` 默认样式：

```css
.el-dialog {
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-xl) !important;
  --el-dialog-padding-primary: var(--sp-6);
}
.el-dialog__header { padding: var(--sp-6) var(--sp-6) 0; }
.el-dialog__body { padding: var(--sp-4) var(--sp-6); }
.el-dialog__footer { padding: 0 var(--sp-6) var(--sp-6); }
```

| 类型 | 宽度 |
|------|------|
| 普通弹窗 | 460–500px |
| 导入/编辑 | 600px |
| 大编辑器 | 800px |

### 4.6 侧栏（SideBar）

```
┌─ SideBar 280px ─────────────────┐
│ ReQCollect          [+ 新建]    │  ← brand area
│ ┌─ 搜索框 ──────────────────┐  │
│ │ 🔍 搜索工作空间/会话...    │  │  ← --radius-sm
│ └───────────────────────────┘  │
│ ▼ 工作空间 (3)                 │  ← collapsible group
│   ├─ 项目Alpha             ○   │  ← hover: --sidebar-hover
│   ├─ 需求分析2026     │    ○   │  ← active: ▽ 3px brand left-indicator
│   │   └── 会话名              │  │                 bg --brand-50
│   └─ 迭代2.0              ○   │  │                 --radius-md
│ ─────────────────────────────  │
│  数据看板  │  用户管理         │
└──────────────────────────────────┘
```

**选中态规范**：
- 左侧 3px `--brand` 竖条指示器（`border-left`）
- 背景 `var(--brand-50)`
- 圆角 `var(--radius-md)`

### 4.7 TopBar

```
┌────────────────────────────────────────────────┐
│  ← 返回         对话区              用户头像 ▼ │
│                  工作空间: 项目Alpha             │
└────────────────────────────────────────────────┘
```

```css
.topbar {
  background: rgba(247, 249, 253, 0.85);
  backdrop-filter: blur(12px);
  box-shadow: 0 1px 0 var(--line), var(--shadow-sm);
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  height: 54px;
}
```

### 4.8 骨架屏

```css
.skeleton {
  background: linear-gradient(90deg, var(--fill) 25%, var(--line-light) 50%, var(--fill) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s var(--ease-in-out) infinite;
  border-radius: var(--radius-sm);
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## 5. 交互与动效

### 5.1 动效时长映射

| 触发场景 | 时长 | 曲线 |
|----------|------|------|
| Hover/点击反馈 | 150ms | `--ease-out` |
| 展开/收起 | 250ms | `--ease-in-out` |
| 弹窗出现 | 250ms | `--ease-out` |
| 页面切换 | 250ms | `--ease-out` |
| 卡片悬浮提升 | 200ms | `--ease-out` |
| 进度环填充 | 600ms | `--ease-out` |
| 消息出现 | 300ms | `--ease-out` |
| 骨架屏 shimmer | 1.5s loop | linear |

### 5.2 3 种标准动效

1. **Fade Slide**（面板/弹窗）：`opacity` + `transform: translateY(4px)` → `(0, 0)`
2. **Scale**（按钮/图标）：`transform: scale(1)` → `scale(1.04)`，仅增强类交互
3. **Elevate**（卡片/容器）：阴影层级 + border-color 双属性过渡

### 5.3 禁止的动效模式

- ❌ 页面加载编排动画（staggered entrance）
- ❌ 无限循环的旋转/闪烁（除骨架屏外）
- ❌ 渐变文字动画
- ❌ 鼠标跟随视差效果
- ❌ 非功能性弹跳/弹性动画

### 5.4 反馈规范

| 交互 | 视觉反馈 |
|------|----------|
| 点击按钮 | 100ms `opacity: 0.85` + 还原 |
| 发送消息 | 按钮 → loading 态 0.3s |
| 操作成功 | 行内 toast `--success-soft` 底 |
| 操作失败 | 弹窗或 toast `--error-soft` 底 |
| 保存成功 | Toast "已保存" 2s 消失 |
| 流式打字 | 光标闪烁 `typingPulse` |

---

## 6. 色彩使用指南

### 6.1 品牌色使用边界

| 色阶 | 用途 | 禁止用途 |
|------|------|----------|
| `--brand-50` | 选中行背景、浅底强调 | ❌ 文字色 |
| `--brand-100` | 用户气泡底色 | ❌ 大面积背景 |
| `--brand-200` | 边框装饰、进度条 | ❌ 主要文字区域 |
| `--brand-500` | 主按钮、链接、指示器 | ❌ 大面积填充 |
| `--brand-600` | Hover/激活、强调文字 | ❌ 默认状态 |
| `--brand-700` | 按下态、深色强调 | ❌ 大面积使用 |

### 6.2 语义色使用场景

| 色值 | 触发场景 |
|------|---------|
| `--success` + `--success-soft` | 操作成功、完整度达标、已连接 |
| `--warning` + `--warning-soft` | 字段缺失、信息不完全、即将超时 |
| `--error` + `--error-soft` | 操作失败、验证错误、连接断开 |
| `--info` + `--info-soft` | 提示信息、引导说明、系统通知 |

### 6.3 文本色层级

| 色值 | 用途 |
|------|------|
| `--text` (#202634) | 正文、标题（默认） |
| `--muted` (#6f7d92) | 次要说明、导航文字 |
| `--muted-light` (#9aa6b8) | 时间戳、辅助标注 |
| `--text-placeholder` (#b0bbcc) | 占位符文字 |

---

## 7. 排版规范

### 7.1 字体栈

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system,
             BlinkMacSystemFont, "Segoe UI", sans-serif;
```

### 7.2 Type Scale

| Token | 字号 | 行高 | 字重 | 应用场景 |
|-------|------|------|------|----------|
| `--text-xs` | 11px | 1.4 | 400 | 时间戳、版本号 |
| `--text-sm` | 13px | 1.5 | 400 | 侧栏项、辅助文字 |
| `--text-base` | 15px | 1.72 | 400 | 正文、消息气泡 |
| `--text-lg` | 17px | 1.6 | 520 | 强调正文 |
| `--text-xl` | 20px | 1.4 | 640 | 卡片标题 |
| `--text-2xl` | 24px | 1.3 | 700 | 页面标题 |
| `--text-3xl` | 28px | 1.25 | 760 | 欢迎大标题 |

### 7.3 代码块

Markdown 渲染的代码块使用 Highlight.js 主题，保持默认样式。代码块字体使用等宽回退：`"Cascadia Code", "Fira Code", "JetBrains Mono", monospace`。

---

## 8. 图标与图片

- **图标库**：全部使用 Element Plus 内置图标（`@element-plus/icons-vue`），不引入第二套图标库
- **图标尺寸**：
  - 16px — 内联文字图标
  - 20px — 按钮内图标
  - 24px — 空状态大图标
- **用户头像**：圆形
  - 30px — 对话框气泡
  - 32px — TopBar
  - 40px — 用户管理页
- **品牌 Logo**：CSS 纯实现渐变圆 Logo，不引入图片资源

---

## 9. 可访问性

| 标准 | 要求 |
|------|------|
| 对比度 | 正文 ≥ 4.5:1，大标题 ≥ 3:1 |
| 焦点指示 | 所有可交互元素有 `:focus-visible` outline（2px solid `--brand` + 3px offset） |
| 动效减弱 | `@media (prefers-reduced-motion: reduce)` 剥离所有动画 |
| 语义标签 | 按钮/链接/图标有 `aria-label` 或 `title` |
| 键盘导航 | Tab 顺序合理，Enter/Space 触发主要操作 |

---

> 本规范为 ReQCollect 前端项目的 UI 设计指导文件。所有新建页面和组件须遵循以上规范。如有疑问，以本规范为准。
