# Plan: 关联目录同步 (后端)

## 1. 任务理解
- 需求来源: Phase 2 Task 2 — Add directory linking, sync, and background watcher to WorkspaceFileManager + DataStore + API
- 核心目标: 允许用户将服务器目录关联到工作空间，支持首次扫描、后台定期同步、取消关联，并提供 REST API 端点

## 2. 改动清单

### 修改文件:
- `app/core/workspace_files.py` — WorkspaceFileManager: 添加 `_ws_id` 跟踪、link/unlink/sync/linked_status 方法、后台线程 watcher (`start_watcher` / `stop_watcher` / `_watcher_loop`)
- `app/db/__init__.py` — DataStore 抽象类: 添加 4 个抽象方法 (link/unlink/sync/linked_status)
- `app/db/compat.py` — FileDataStore: 实现 4 个新抽象方法
- `app/db/repository.py` — MySQLDataStore: 实现 4 个新抽象方法
- `app/api/workspace.py` — 添加 4 个新 API 端点 (POST link, POST unlink, POST sync, GET linked-status)

## 3. 数据模型
- 无新增表/字段
- 关联路径以文件形式存储: `<data_dir>/workspaces/<ws_id>/.linked_path`
- 后台 watcher 以模块级 dict 维护线程状态

## 4. 验收标准

- [ ] P0: POST `/api/workspaces/{id}/link` 接受 directory path 并返回扫描结果
- [ ] P0: POST `/api/workspaces/{id}/unlink` 取消关联并返回移除文件数
- [ ] P0: POST `/api/workspaces/{id}/sync` 手动触发重新扫描
- [ ] P0: GET `/api/workspaces/{id}/linked-status` 返回当前关联状态
- [ ] P0: 链接的文件在 index 中标记为 `"source": "linked"` 并记录 `abs_path`
- [ ] P1: 后台 watcher 每 300s 自动同步
- [ ] P1: 无效目录返回 400 错误
- [ ] P1: 不存在的 workspace 返回 404

## 5. 风险与依赖
- 依赖已存在的 WorkspaceFileManager 基础方法 (list_files, read_file, read_file_section..)
- WorkspaceFileManager.__init__ 需添加 `_ws_id` 属性
- watcher 线程需守护模式，避免阻止进程退出
- 无其他风险

## 6. 实施步骤 (按顺序)
1. 修改 `app/core/workspace_files.py`: 添加 `_ws_id`、添加模块级 watcher、添加实例方法 (link/unlink/sync/status/scan)
2. 修改 `app/db/__init__.py`: 添加 4 个抽象方法
3. 修改 `app/db/compat.py`: 实现 FileDataStore 的 4 个新方法
4. 修改 `app/db/repository.py`: 实现 MySQLDataStore 的 4 个新方法
5. 修改 `app/api/workspace.py`: 添加 4 个新 API 端点
6. 验证: 运行检查命令确认路由注册
