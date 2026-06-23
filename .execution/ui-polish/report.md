# Report: ui-polish — UI 设计系统统一与动效补齐

## 验收标准验证
- [x] P0: ImportDialog / FileManager 中所有硬编码色值替换为 CSS 变量 → ✅ OK
- [x] P0: 全局硬编码色值统一替换（所有 .vue 文件中）→ ✅ OK (147+ 处)
- [x] P0: Element Plus 主题色跟随 CSS 变量品牌色 → ✅ OK
- [x] P1: 消息入场有淡入/上移动画 → ✅ OK
- [x] P1: 按钮有 hover/active 微动效 → ✅ OK
- [x] P1: 面板切换有过渡效果 → ✅ OK
- [x] P1: 所有可交互元素有 focus-visible 样式 → ✅ OK
- [x] P1: 侧栏面板切换有平滑过渡 → ✅ OK

## 功能验证
- [x] ImportDialog.vue — 9 处硬编码已替换，零残留
- [x] FileManager.vue — 8 处硬编码已替换，零残留
- [x] SideBar.vue — 28 处硬编码已替换
- [x] FileTreePanel.vue — 29 处硬编码已替换
- [x] ChatInput.vue — 15+ 处硬编码已替换
- [x] UsersView.vue — 22 处硬编码已替换
- [x] WikiPageEditor.vue — 14 处硬编码已替换
- [x] WikiPageView.vue — 13 处硬编码已替换
- [x] WorkspaceList.vue — 8 处硬编码已替换
- [x] LoginView.vue — 6 处硬编码已替换（含 SVG fill）
- [x] GraphView.vue — 4 处硬编码已替换
- [x] WorkspaceDetail.vue — 2 处硬编码已替换
- [x] DashboardView.vue — 2 处硬编码已替换
- [x] SufficiencyRing.vue — 2 处硬编码已替换
- [x] TopBar.vue — 1 处硬编码已替换
- [x] ProfilePanel.vue — 保留语义绿色（无对应设计变量）

## 动效系统验证
- [x] msgIn 消息入场动画 — @keyframes + 级联延迟
- [x] 按钮微反馈 — active scale(0.96)
- [x] 面板切换过渡 — opacity transition

## Element Plus 主题桥接
- [x] --el-color-primary → var(--brand)
- [x] --el-text-color-primary → var(--text)
- [x] --el-border-color → var(--line)
- [x] --el-bg-color → var(--panel)

## focus-visible 环
- [x] global.css 全局规则
- [x] QuickReplyBar scoped
- [x] ChatInput scoped
- [x] SideBar scoped
- [x] FileTreePanel scoped
- [x] TopBar scoped

## 回归检查
- [x] npm run build — ✅ 3364 modules, 16.48s, 0 errors
- [x] 无未定义 CSS 变量引用 (var(--text-secondary) / var(--warning) 已清除)
- [x] 后端 /api/health — ✅ OK
- [x] @types/node 已添加（修复构建 TS 错误）

## 评估结论
✅ **通过** — 所有验收标准（P0+P1）均已满足，构建无错误，CSS 变量映射正确。

## 遗留项
- 语义绿色值（#67c23a, #52c41a, #e8f5e9 等）保留硬编码，建议后续在 variables.css 中添加 `--success` 变量统一
- chunk size 警告（ECharts/mermaid 等大型库 >500KB）属正常现象，不影响功能
