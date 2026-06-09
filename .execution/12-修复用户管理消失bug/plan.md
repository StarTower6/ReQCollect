# Plan: 12 — 修复页面刷新后用户管理选项消失

## 1. 任务理解
- Issue #5: 页面刷新后点击用户头像，"用户管理"选项消失
- 根因: 刷新页面后 AuthStore 的 token 从 localStorage 恢复，但 `user` 对象为 null（需要调用 `/api/auth/me` 加载）
- `isAdmin` computed 依赖 `authStore.user?.role` → user 为 null → isAdmin = false → 菜单项不显示

## 2. 改动清单
- 修改: `reqcollect-web/src/stores/auth.ts` — 添加 `init()` 方法，从 token 恢复时自动加载用户信息
- 或在 App.vue 或 AppLayout.vue 挂载时调用 `authStore.loadUser()`

## 3. 验收标准
- [ ] P0: 页面刷新后用户管理选项仍然可见（admin 用户）
- [ ] P0: 非管理员看不到"用户管理"选项

## 4. 实施步骤
1. 在 auth.ts 中加 `init()`，存 token 时自动 `loadUser()`
2. 或让 App.vue onMounted 时调用
3. 验证
