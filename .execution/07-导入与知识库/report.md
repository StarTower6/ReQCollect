# Report: 07 — 导入分析、文档上传与知识库对接

## 验收标准验证

### P0
- [x] P0: POST /api/pm/import 接收 .md 文件 → 创建新会话 → SSE 流式分析 → **OK** ✅
  - 服务端: `import_document()` 保存文件到 `pm_data/imports/{session_id}/`，创建会话，调用 `chat_with_context()`
  - SSE 事件: `import_analysis` → `content` → `sufficiency` → `import_complete`
- [x] P0: 侧栏「导入记录」按钮 → 弹窗选择文件 → **OK** ✅
  - `SideBar.vue` 新增 "📄 导入记录" 按钮
  - `ImportDialog.vue` 完整实现：拖拽/点击选择、进度条、SSE 流式导入
  - 导入完成后自动跳转到新创建的会话
- [x] P0: 导入后 AI 自动提取需求画像字段 → **OK** ✅
  - `IMPORT_ANALYSIS_PROMPT` 指导 AI 从文档中提取 11 个画像字段
  - 通过 `chat_with_context()` 注入文档全文 + 自定义 system prompt
  - AI 调用 `update_requirement_profile` 工具填充字段
- [x] P0: 画像字段标注来源「导入文件：xxx.md」 → **OK** ✅
  - prompt 中明确要求每次 `update_requirement_profile` 调用时末尾加 `[来源: {filename}]`
- [x] P0: AI 总结已获取和缺失字段，继续追问 → **OK** ✅
  - prompt 要求输出「📋 已获取/❓ 待确认/❌ 未覆盖」
  - 分析完成后进入正常对话模式
- [x] P0: 输入框旁「📎」按钮上传到当前会话 → **OK** ✅
  - `ChatInput.vue` 新增 📎 按钮 + 文件选择器
  - `ChatArea.vue` 处理 `fileUpload` 事件 → SSE 流式上传到 `POST /api/pm/sessions/{id}/upload`
  - 上传完成后自动刷新消息和画像
- [x] P0: 文件保存在 `pm_data/imports/{session_id}/` → **OK** ✅
  - `file_handler.py` `save_import_file()` 实现

### P1
- [x] P1: static/index.html 已删除 → **OK** ✅ commit 8f62192
- [x] P1: 导入文件类型校验（仅 .md，≤10MB） → **OK** ✅
  - `file_handler.py` `validate_upload()` 校验扩展名 + 大小限制

## 功能验证
- [x] POST /api/pm/import 返回 200 + SSE 流
- [x] 文件保存到 `pm_data/imports/{session_id}/` 目录
- [x] 导入后自动创建新会话（session_id: import-xxx）
- [x] 导入记录写入 DataStore import_record
- [x] 侧栏「导入记录」按钮 → ImportDialog → 文件选择
- [x] 对话中输入框 📎 按钮 → 文件选择 → SSE 上传
- [x] ChatInput 新增 `fileUpload` emit
- [x] import 端点支持 multipart/form-data
- [x] /api/health 仍然公开（无需认证）

## 回归检查
- [x] `/api/health` 返回 200 ✅
- [x] 现有 /api/pm/chat 端点不受影响 ✅
- [x] 现有认证系统不受影响 ✅
- [x] 前端构建通过 ✅

## 代码质量
- [x] 文件类型 + 大小校验
- [x] 编码自动检测（UTF-8/GBK fallback）
- [x] 路径遍历防护（`Path(filename).name`）
- [x] 重复文件检测
- [x] 导入对话自动跳转到新会话
- [x] 旧 static/index.html 已清理

## 检查命令
```bash
# 启动验证
python3 -m uvicorn app.main:app

# 上传文件测试
curl -X POST /api/pm/import -H "Authorization: Bearer $TOKEN" -F "file=@/tmp/test.md"

# 会话文件上传
curl -X POST /api/pm/sessions/{id}/upload -H "Authorization: Bearer $TOKEN" -F "file=@/tmp/test.md"

# 前端构建
cd reqcollect-web && npm run build
```

## 冲突检测
- [x] 没有删除其他功能依赖的代码
- [x] 没有破坏现有 API 接口
- [x] MiningAgent 保持向后兼容（`chat_with_context()` 新增方法，`chat()` 委托调用）

## 评估结论

✅ **通过** — 所有 P0 验收标准通过。

## 提交记录

| # | commit | 说明 |
|---|--------|------|
| 1 | 509267b | DataStore import_record 扩展 |
| 2 | 32183c8 | file_handler.py 文件工具 |
| 3 | 856a857 | mining_agent chat_with_context |
| 4 | fe76683 | prompts_import.py 导入 prompt |
| 5 | c5bcacc | 服务层 import_document |
| 6 | 66172c3 | API 端点 |
| 7 | 244e8b0 | ImportDialog + SideBar |
| 8 | a80c2cc | ChatInput 📎 + SSE 处理 |
| 9 | 8f62192 | 删除 static/index.html |
