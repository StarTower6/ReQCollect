# Plan: PPTX/Image 文件解析管线

## 1. 任务理解
- 需求来源: docs/requirements/04-存储与数据/ 模块要求 — 扩展文件类型支持至 PPTX 和图片
- 核心目标: 在现有 docx/xlsx 解析基础上，增加 pptx 文本提取和图片元数据提取能力

## 2. 改动清单
- 修改文件:
  - app/core/file_handler.py — ALLOWED_EXTENSIONS 增加 pptx 和图片扩展名
  - app/core/workspace_files.py — 新增 parse_pptx / parse_image / is_image_ext 函数，修改 read_file 分支
  - pyproject.toml — office 可选依赖增加 python-pptx、Pillow

## 3. 数据模型
无变更 — 纯解析层扩展

## 4. 验收标准
- [ ] P0: ALLOWED_EXTENSIONS 包含 pptx/png/jpg/jpeg/gif/bmp
- [ ] P0: parse_pptx 能从 .pptx 文件中提取幻灯片文本
- [ ] P0: parse_image 能提取图片的格式/尺寸/模式元数据
- [ ] P0: is_image_ext 正确识别 png/jpg/jpeg/gif/bmp
- [ ] P0: read_file 方法能通过扩展名正确分派到 parse_pptx/parse_image
- [ ] P1: pyproject.toml office 组包含 python-pptx >=0.6.23 和 Pillow
- [ ] P1: 导入验证通过: `from app.core.workspace_files import WorkspaceFileManager, parse_pptx, parse_image, is_image_ext`

## 5. 风险与依赖
- 需要安装 python-pptx 和 Pillow 库
- 不影响现有 text/docx/xlsx 解析路径
- office 可选依赖组会扩展安装范围

## 6. 实施步骤 (按顺序)
1. 修改 ALLOWED_EXTENSIONS
2. 添加 parse_pptx / parse_image / is_image_ext 函数
3. 修改 read_file 方法
4. 更新 pyproject.toml 可选依赖
5. 安装依赖并验证
6. 提交
