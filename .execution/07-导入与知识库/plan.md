# Plan: 07 — 导入分析、文档上传与知识库对接

## 1. 任务理解
- 需求来源: `docs/requirements/07-导入与知识库/README.md`
- 核心目标: 实现 `.md` 文件导入分析，AI 自动提取需求画像字段。
  双入口：侧栏「导入记录」新建会话 + 输入框「📎」上传到当前会话

## 2. 改动清单

### 新增文件
- `app/core/file_handler.py` — 文件保存/路径工具
- `app/agent/pm/prompts_import.py` — 导入分析专用 system prompt
- `reqcollect-web/src/components/chat/ImportDialog.vue` — 导入弹窗
- 删除 `static/index.html`

### 修改文件
- `app/agent/pm/phase1/mining_agent.py` — 新增 `chat_with_context()` 方法
- `app/agent/pm/tools.py` — 新增 `_field_sources` 存储 + 来源标记工具
- `app/db/__init__.py` — DataStore 新增 import_record 方法
- `app/db/compat.py` — FileDataStore 实现 import_record
- `app/db/repository.py` — MySQLDataStore 实现 import_record
- `app/api/pm.py` — 新增 import/upload 端点
- `app/services/pm_agent_service.py` — 新增 `import_document()`, `upload_session_file()`
- `reqcollect-web/src/api/client.ts` — 新增文件上传方法
- `reqcollect-web/src/components/chat/ChatInput.vue` — 添加 📎 上传按钮
- `reqcollect-web/src/components/chat/ChatArea.vue` — 附件 chip + 导入事件处理
- `reqcollect-web/src/components/layout/SideBar.vue` — 「导入记录」按钮
- `reqcollect-web/src/views/ChatView.vue` — 处理 import SSE 事件

## 3. 数据模型
- 新增 `import_records` 概念：
  - 文件存储: `pm_data/imports/{session_id}/{filename}`
  - DataStore 方法: `save_import_record()`, `get_import_records()`
- 画像元数据: `_field_sources: dict[str, str]` 映射字段名 → 来源文件名

## 4. 验收标准
- [ ] P0: POST /api/pm/import 接收 .md 文件 → 创建新会话 → SSE 流式分析
- [ ] P0: 侧栏「导入记录」按钮 → 弹窗选择文件
- [ ] P0: 导入后 AI 自动提取需求画像字段
- [ ] P0: 画像字段标注来源「导入文件：xxx.md」
- [ ] P0: AI 总结已获取和缺失字段，继续追问
- [ ] P0: 输入框旁「📎」按钮上传到当前会话
- [ ] P0: 文件保存在 `pm_data/imports/{session_id}/`
- [ ] P1: static/index.html 已删除（Vue SPA 替代）
- [ ] P1: 导入文件类型校验（仅 .md，≤10MB）

## 5. 风险与依赖
- MiningAgent 的 MemorySaver 历史不能直接修改 — 通过 `chat_with_context()` 注入上下文
- 当前会话上传需要在下次 chat 时注入文档内容作为 system 消息
- .md 文件需解析为纯文本，由 LLM 提取字段

## 6. 实施步骤 (按顺序)
1. DataStore: import_record 抽象 + 实现
2. file_handler.py: 文件保存工具
3. mining_agent.py: chat_with_context()
4. prompts_import.py: 导入分析 system prompt
5. pm_agent_service.py: import_document() + upload_session_file()
6. api/pm.py: 新端点
7. 前端: ImportDialog + SideBar 导入按钮
8. 前端: ChatInput 📎 按钮
9. 前端: SSE 事件处理 + 附件展示
10. 清理 static/index.html
11. 测试 + 验证
