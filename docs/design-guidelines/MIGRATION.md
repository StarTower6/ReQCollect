# 设计令牌迁移指南

> 从 v0 (当前) 设计变量迁移到 v1 "Warm Current" 规范的映射关系

## 变量迁移映射

| 旧变量 (v0) | 新变量 (v1) | 说明 |
|-------------|-------------|------|
| `--bg` | `--bg` | 保留不变 |
| `--sidebar` | `--sidebar` | 保留不变 |
| `--sidebar-hover` | `--sidebar-hover` | 保留不变 |
| `--panel` | `--panel` | 保留不变 |
| `--line` | `--line` | 保留不变 |
| `--line-strong` | `--line-strong` | 保留不变 |
| — | `--line-light` | 新增 |
| — | `--fill` | 新增 |
| `--text` | `--text` | 保留不变 |
| `--muted` | `--muted` | 保留不变 |
| `--muted-light` | `--muted-light` | 保留不变 |
| — | `--text-placeholder` | 新增 |
| `--brand` | `--brand` / `--brand-500` | 保留，增加别名 |
| `--brand-dark` | `--brand-dark` / `--brand-600` | 保留，增加别名 |
| `--brand-soft` | `--brand-soft` / `--info-soft` | 保留，增加别名 |
| — | `--brand-50` | 新增色阶 |
| — | `--brand-100` | 新增（替代 `#e8f1ff` 用户气泡底色） |
| — | `--brand-200` | 新增 |
| — | `--brand-400` | 新增（= `--info`） |
| — | `--brand-700` | 新增 |
| — | `--success` / `--warning` / `--error` / `--info` | 新增语义色 |
| — | `--*-soft` | 新增语义浅底 |
| `--radius` | `--radius-sm` | 旧 8px → 新命名 |
| — | `--radius-xs` / `--radius-md` / `--radius-lg` / `--radius-xl` | 新增 |
| `--shadow` | `--shadow-xl` | 重命名 |
| — | `--shadow-sm` / `--shadow-md` / `--shadow-lg` | 新增阴影等级 |

## 逐步迁移建议

### 第一步：variables.css 替换（无破坏性）

在 `variables.css` 中追加新变量，旧变量保留为别名：

```css
:root {
  /* v0 兼容变量 — 保留不动 */
  --bg: #f7f9fd;
  --sidebar: #f2f5fb;
  /* ... 全部保留 ... */

  /* v1 新增变量 — 追加在末尾 */
  --brand-50: #eef4ff;
  --brand-100: #dbe7fe;
  --brand-200: #b6cefd;
  --brand-400: #6b9ff8;
  --brand-700: #1a4da8;
  /* ... */
}
```

### 第二步：全局圆角升级

- `variables.css` 中旧 `--radius` 保留为 `--radius-sm`
- 新增 `--radius-md`(12px)、`--radius-lg`(16px)
- 各组件逐步从 `var(--radius)` 迁移到更具体的圆角变量

### 第三步：组件样式更新

逐个组件迁移，从高可见度组件开始：

1. **Card** → `--radius-lg` + hover shadow
2. **Dialog** → `--radius-lg` + `--shadow-xl`
3. **Message Bubble** → `--radius-md` + `--shadow-sm`
4. **ChatInput** → focus glow ring
5. **SideBar** → 选中指示条

---

> 迁移原则：向后兼容，逐步推进。不要求一次性全部改完。
