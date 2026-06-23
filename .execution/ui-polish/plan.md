# Plan: ui-polish — UI 设计系统统一与动效补齐

## 1. 任务理解
- 来源: UI 设计师的设计评审建议
- 核心目标: 统一前端硬编码色值、补齐动效系统、建立 Element Plus 主题桥接、补齐键盘可访问性

## 2. 改动范围

### 模块 A: 统一硬编码色值
在以下组件中将硬编码颜色替换为 CSS 变量（variables.css）:
- `components/chat/ImportDialog.vue` — 9 处硬编码色值
- `components/workspace/FileManager.vue` — 8 处硬编码色值
- `views/wiki/WikiPageEditor.vue` — 14 处硬编码色值
- `views/LoginView.vue` — 6 处硬编码色值
- `components/chat/ChatInput.vue` — 15 处硬编码色值
- `components/layout/SideBar.vue` — 28 处硬编码色值
- `components/workspace/FileTreePanel.vue` — 29 处硬编码色值
- `views/admin/UsersView.vue` — 22 处硬编码色值
- `views/wiki/WikiPageView.vue` — 13 处硬编码色值
- `views/WorkspaceList.vue` — 8 处硬编码色值
- `views/wiki/GraphView.vue` — 4 处硬编码色值
- `views/WorkspaceDetail.vue` — 2 处硬编码色值
- `views/DashboardView.vue` — 2 处硬编码色值
- `components/profile/SufficiencyRing.vue` — 2 处硬编码色值
- `components/profile/ProfilePanel.vue` — 1 处硬编码色值
- `components/layout/TopBar.vue` — 1 处硬编码色值

### 模块 B: 补齐动效系统
- 消息入场动画（MessageBubble 进入淡入/上移）
- Composer 按钮反馈（微缩放到点击反馈）
- 侧栏面板切换平滑过渡
- SufficiencyRing 进度动画

### 模块 C: Element Plus 主题桥接
- 将 CSS 变量映射到 Element Plus CSS 变量（`--el-color-primary` 等）
- 在 global.css 中添加 Element Plus 变量覆盖

### 模块 D: focus-visible 环
- 为所有可交互元素补齐 `focus-visible` 样式
- 按钮、输入框、侧栏项、快速回复按钮等

## 3. 验收标准

- [ ] P0: ImportDialog / FileManager 中所有硬编码色值替换为 CSS 变量
- [ ] P0: 全局硬编码色值统一替换（所有 .vue 文件中）
- [ ] P0: Element Plus 主题色跟随 CSS 变量品牌色
- [ ] P1: 消息入场有淡入/上移动画
- [ ] P1: 按钮有 hover/active 微动效
- [ ] P1: 面板切换有过渡效果
- [ ] P1: 所有可交互元素有 focus-visible 样式
- [ ] P1: 侧栏面板切换有平滑过渡

## 4. 风险与依赖
- 需确保 CSS 变量替换后视觉效果不变
- Element Plus 2.x CSS 变量查看是否在当前版本支持
- 动效使用 CSS transition/animation，不引入第三方动画库

## 5. 角色分工（调整后）
- **UI设计师** → 定义设计规范（色值映射表）、动效系统（global.css）、Element Plus 主题桥接（global.css）
- **前端开发者** → 按映射表执行所有 .vue 组件文件的硬编码色值替换、focus-visible 环
- **后端开发者** → 本次不参与 UI 工作

## 6. 实施步骤
1. UI设计师: 提供色值映射表（传递给前端开发者）
2. 前端开发者: ImportDialog + FileManager 硬编码色值替换
3. 前端开发者: 补齐 focus-visible 环（组件级）
4. 前端开发者: 按映射表执行全局 14 个组件色值替换
5. UI设计师: 修改 global.css 补齐动效系统
6. UI设计师: 建立 Element Plus 主题桥接
7. Evaluate: 回归检查所有页面效果
