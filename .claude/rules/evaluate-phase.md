# PGE 三段式 — Evaluate（评估阶段）

## 目标

验证生成结果满足需求文档中的验收标准，无引入新问题。

将评估结果写入 `.execution/<feature-name>/report.md`：

```markdown
# Report: <功能名称>

## 验收标准验证
- [ ] P0: ... → OK
- [ ] P0: ... → FAILED
- [ ] P1: ... → OK

## 功能验证
- [ ] 需求文档中的功能点都覆盖了？
- [ ] API 端点返回正确的 HTTP 状态码？
- ...

## 回归检查
- [ ] /api/health 返回 200？
- ...

## 评估结论
✅ 通过 / ❌ 需要修复 / ⚠️ 有风险但可用

## 修复建议（如有）
- ...
```

写入 report.md 后，PostToolUse hook 会自动提交所有改动（plan.md + tasks.md + report.md + 代码）并推送到 GitHub。无需手动 git push。

## 验证清单

### 0. 验收标准逐条验证
对照 Plan 阶段输出的验收标准，逐条打勾：
- [ ] P0: ... → OK / FAILED
- [ ] P1: ... → OK / FAILED

### 0.1 tasks.md 完成度验证
- [ ] tasks.md 中所有条目均为 `- [x]`（没有遗漏）
- [ ] 每个任务的 commit 引用已记录
- [ ] 未被 `- [ ]` 遗漏的未完成任务

所有 **P0 必须全过** 才能算通过。P1 未过需标注但不阻塞发布。

### 1. 功能验证
- [ ] 需求文档中的功能点都覆盖了？
- [ ] API 端点返回正确的 HTTP 状态码？
- [ ] 前端页面正常渲染、交互可用？

### 2. 回归检查
- [ ] `/api/health` 返回 200？
- [ ] 现有页面没有报错？
- [ ] 依赖没有冲突？

### 3. 代码质量
- [ ] 没有硬编码的密码/API Key
- [ ] 配置文件遵循 .env.example 模式
- [ ] 新文件有必要的 import/引用

### 4. 检查命令
```bash
# 检查 Python 语法
python3 -c "import ast; ast.parse(open('app/main.py').read())"

# 检查 API 端点
curl -s http://localhost:9900/api/health

# 检查新增文件是否可导入
python3 -c "from <module> import <function>"
```

### 5. 冲突检测
- [ ] 没有删除其他功能依赖的代码
- [ ] 没有破坏 CSS 设计变量的一致性
- [ ] 没有引入重复功能（先查是否有现成实现）

## 输出格式

```markdown
## 评估报告

### 通过项
- ...

### 未通过项
- ...
  - 修复方案: ...

### 建议
- ...

### 结论
✅ 通过 / ❌ 需要修复 / ⚠️ 有风险但可用
```

## 原则

- **先评估再提交** — generate 完成后必须 evaluate，不得跳过
- **失败回退** — 评估未通过 → 返回 Plan 阶段修正 → 重新 Generate
- **诚实报告** — 不要隐藏问题，"有小问题但不影响主体功能"也要说出来
