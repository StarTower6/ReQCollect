# PGE 三段式 — Generate（生成阶段）

## 目标

按 Plan 阶段的计划实施，生成可运行的代码。

## 规则

### 0. 严格按计划执行（核心规则）

从 `plan.md` 提取任务清单到 `.execution/<feature-name>/tasks.md`：

```markdown
# Tasks: <功能名称>

## 任务清单
- [ ] 任务1: 实现 xxx — 负责人: Claude Code Agent
- [ ] 任务2: 实现 yyy — 负责人: Claude Code Agent
- [ ] 任务3: 实现 zzz — 负责人: sub-agent-1
```

- 任务可以分配给多个子 agent 并行执行
- **只做 tasks.md 中的内容**，不做任何额外改动

### 0.1 实时同步 tasks.md（重要）
- **每完成一个任务，立即更新 tasks.md** 将对应的 `- [ ]` 改为 `- [x]`
- 更新 tasks.md 后立即 `git add` 和 `git commit`（引用任务名）
- 不允许攒到 Evaluate 阶段再统一改 tasks.md
- 示例：
  ```
  # 任务完成前
  - [ ] 任务1: 实现 database.py
  
  # 任务完成后 → 立即改为
  - [x] 任务1: 实现 database.py — commit: abc1234
  ```
- 如果使用了子 agent 并行执行，主 agent 在合并结果时一并更新 tasks.md
- 最终 Evaluate 阶段 tasks.md 中所有条目应均为 `- [x]` 状态
- 如果发现计划遗漏了某些明显需要做的事情：
  1. 停下来
  2. 标注"计划外发现: xxx"
  3. 等用户决策是否加入当前轮次还是留到下轮
- 严禁"顺便改一下"、"顺便优化一下"、"顺便修个别的 bug"
- 除非是直接阻碍当前任务的问题（如文件不存在、依赖缺失），否则一律不做额外改动

### 1. 代码风格
- Python: 类型注解 + Google style docstring
- Python 缩进: 4 空格
- HTML/CSS: 2 空格缩进
- 前端: 保留现有 CSS 设计系统变量，不引入新框架
- 所有函数需要类型注解，所有方法需要 docstring

### 2. 提交规范
- 每次功能完成立即 commit（post-commit hook 自动 push）
- commit message 格式: `<type>: <description>`
  - `feat:` — 新功能
  - `fix:` — 修复
  - `refactor:` — 重构
  - `docs:` — 文档
  - `chore:` — 杂项

### 3. 可用技能
当任务匹配时，自动加载以下技能：
- `design` — UI/UX 设计 (配色、排版、图标)
- `impeccable` — 设计打磨 (polish, layout, typeset)
- `gitnexus` — 代码图查询 (context, impact, query)

### 4. 依赖管理
- Python 依赖: 更新 pyproject.toml
- 前端的第三方库: 用 CDN 引入，不用 npm 打包

### 5. 不要做的事
- ❌ 不要改 /api/pm/* 的路径结构
- ❌ 不要把前端转成 React/Vue
- ❌ 不要引入新的构建工具链
- ❌ 不要删除 .git/hooks/ 文件
