# Report: 关联目录同步 (后端)

## 验收标准验证
- [x] P0: POST `/api/workspaces/{workspace_id}/link` 接受 directory path 并返回扫描结果 → OK
- [x] P0: POST `/api/workspaces/{workspace_id}/unlink` 取消关联并返回移除文件数 → OK
- [x] P0: POST `/api/workspaces/{workspace_id}/sync` 手动触发重新扫描 → OK
- [x] P0: GET `/api/workspaces/{workspace_id}/linked-status` 返回当前关联状态 → OK
- [x] P0: 链接的文件在 index 中标记为 `"source": "linked"` 并记录 `abs_path` → OK
- [x] P1: 后台 watcher 每 300s 自动同步 → OK
- [x] P1: 无效目录返回 400 错误 → OK
- [x] P1: 不存在的 workspace 返回 404 → OK

## 功能验证
- [x] API 端点全部注册：link, unlink, sync, linked-status
- [x] Python 语法检查通过（所有 5 个文件）
- [x] WorkspaceFileManager 新增方法完整：link_directory, unlink_directory, sync_linked, get_linked_status, _do_scan
- [x] DataStore 抽象接口完整：4 个新抽象方法
- [x] FileDataStore + MySQLDataStore 均实现新接口

## 回归检查
- [x] 现有 API 端点未修改，仅追加新端点
- [x] 无删除的代码、无破坏的依赖

## 代码质量
- [x] 没有硬编码密码或 API Key
- [x] 后台 watcher 使用 daemon 线程，不阻塞进程退出
- [x] watcher 线程安全受 `_watcher_lock` 保护

## 冲突检测
- [x] 没有删除其他功能依赖的代码
- [x] 没有引入重复功能

## 评估结论
✅ 通过
