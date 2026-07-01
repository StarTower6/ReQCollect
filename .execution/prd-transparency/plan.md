# Plan: prd-transparency — PRD 生成透明化 + 存储与查看重构

## 1. 任务理解

### 当前问题
1. **生成过程不透明** — 用户只看到进度条和章节名，看不到 AI 思考过程和实时生成内容
2. **PRD 查看入口缺失** — 从需求池生成 PRD 后跳转 `/prd/{prd_id}`，但 PrdView 按 `session_id` 查询，查不到
3. **工作空间无 PRD 列表** — 生成完找不到在哪看
4. **PRD 按 session 存储** — 但新流程是从提案池生成，没有对应 session

### 核心目标
1. 生成 PRD 时让用户看到**思考过程** + **实时 markdown 内容**
2. PRD **按 workspace 存储**，工作空间有 PRD 列表页
3. PRD 详情页**按 prd_id 查看**（不再依赖 session_id）
4. 生成完成后跳转到 PRD 详情页能正常打开

---

## 2. 数据模型调整

### GeneratedPRD 表结构（现状）
```
id, session_id, version, title, mode, source_proposal_ids, sections, markdown, created_at
```
- `session_id` NOT NULL — 从会话生成时用，从提案池生成时为空字符串

### 调整方案（不改表结构，加可空字段）
```python
# GeneratedPRD 新增字段
workspace_id: str = ""        # PRD 所属工作空间（从提案池生成时必填）
```
- 不改 `session_id`（保持兼容），新增 `workspace_id`
- 从提案池生成时：`workspace_id` 必填，`session_id` 可空
- 从会话生成时：`session_id` 必填，`workspace_id` 从 session 推导

---

## 3. 技术方案

### A) 后端 — 增加思考过程事件（assembler.py + planner.py）

#### A1: planner.plan() 返回时附带思考
```python
def plan(self, profile, mode="one_shot") -> tuple[list[dict], list[str]]:
    scene = self.recognizer.recognize(profile)
    thoughts = [
        f"识别项目场景：{scene_config['label']}",
        f"根据场景选择 {len(sections)} 个章节，重点章节：{重点字段列表}",
        f"采用{'流式生成' if mode=='one_shot' else '逐章生成'}模式"
    ]
    return sections, thoughts
```

#### A2: assembler.assemble() yield thought 事件
```python
# 每章生成前
yield {
    "type": "thought",
    "data": {"phase": "section_start", "text": f"撰写「{section['title']}」——这一章是 PRD 的核心，需要详细描述..."}
}
# 场景识别后
yield {"type": "thought", "data": {"phase": "planning", "text": "..."}}
```

### B) 后端 — PRD 按 workspace 存储（pm.py + DataStore）

#### B1: `generate-from-proposals` 端点保存时记录 workspace_id
```python
saved = await ds.save_prd(
    session_id=request.session_id or "",  # 可空
    workspace_id=request.workspace_id,    # 新增
    ...
)
```

#### B2: DataStore.save_prd() 增加 workspace_id 参数
#### B3: 新增 `list_prds_by_workspace(workspace_id)` 方法
#### B4: 新增 `get_prd_by_id(prd_id)` 方法（按主键查，不依赖 session）

### C) 后端 — 新增 PRD 查看端点

| 端点 | 说明 |
|------|------|
| `GET /api/workspaces/{id}/prds` | 列出工作空间的所有 PRD |
| `GET /api/pm/prd/by-id/{prd_id}` | 按 PRD ID 查看详情（新增，不依赖 session） |

### D) 前端 — PRD 查看入口重构

#### D1: 路由调整
```typescript
// 现有（保留兼容）
{ path: '/prd/:id', name: 'Prd', component: PrdView }  // :id 可以是 sessionId 或 prdId

// 新增
{ path: '/workspaces/:id/prds', name: 'WorkspacePrds', component: PrdListView }
```

#### D2: PrdView.vue 改造
- `onMounted` 优先用 `getPrdById(id)`，fallback 到 `fetchPrd(sessionId)`
- 这样 `/prd/{prd_id}` 和 `/prd/{session_id}` 都能工作

#### D3: 新增 PrdListView.vue（工作空间 PRD 列表）
- 显示工作空间下所有 PRD（标题、生成时间、来源）
- 点击卡片跳 `/prd/{prd_id}`

#### D4: WorkspaceDetail.vue 加"PRD 文档"Tab
- 在会话列表、Wiki、文件、图谱、提案之后加 Tab

### E) 前端 — 生成过程透明化（ProposalListView + ChatView）

#### E1: generatePrd 进度对话框改造
```vue
<el-dialog v-model="showPrdDialog" width="900px">
  <div class="prd-gen-dialog">
    <!-- 左侧：思考过程 + 进度 -->
    <div class="prd-gen-left">
      <div class="prd-gen-thoughts">
        <div v-for="t in thoughts" class="thought-item">{{ t }}</div>
      </div>
      <el-progress :percentage="progress" />
      <div class="prd-gen-status">{{ statusText }}</div>
    </div>
    <!-- 右侧：实时 markdown 渲染 -->
    <div class="prd-gen-right">
      <div class="prd-gen-preview" v-html="renderedPreview"></div>
    </div>
  </div>
</el-dialog>
```

#### E2: SSE 事件处理
```typescript
// section_content token 累加到 previewMarkdown
if (event.type === 'section_content') {
  previewMarkdown.value += event.data
  renderedPreview.value = marked.parse(previewMarkdown.value)
}
// thought 事件加到 thoughts 列表
if (event.type === 'thought') {
  thoughts.value.push(event.data.text)
}
```

---

## 4. 验收标准

### P0（核心）
- [ ] planner 识别场景后 yield `thought` 事件
- [ ] assembler 每章生成前 yield `thought` 事件
- [ ] 前端生成对话框显示思考过程 + 实时 markdown
- [ ] `GET /api/pm/prd/by-id/{prd_id}` 端点
- [ ] `GET /api/workspaces/{id}/prds` 端点
- [ ] PrdView 按 prd_id 查看正常
- [ ] 工作空间详情页有"PRD 文档"Tab
- [ ] 从需求池生成 PRD 完成后跳转能正常打开

### P1（体验）
- [ ] PrdListView 显示 PRD 列表
- [ ] PRD 列表显示来源（从提案池/从会话）
- [ ] 思考过程有动画/滚动效果

---

## 5. 风险与依赖
- `generated_prds.workspace_id` 加字段需迁移（幂等）
- PrdView 路由 `/prd/:id` 的 `:id` 语义模糊（session_id 还是 prd_id）—— 用 try/fallback 策略
- 不改现有 `/api/pm/prd/{session_id}` 端点（兼容）

---

## 6. 角色分工（全栈模式）

| 角色 | 队友 | 任务 |
|------|------|------|
| 全栈 | 全栈开发者 | A) 思考事件 + B) workspace 存储重构 + C) 新端点 + D) 前端入口 + E) 透明化 UI |
| 设计 | UI设计师 | 进度对话框的双栏布局样式（思考流 + markdown 预览） |

---

## 7. 实施步骤

1. 全栈: planner/assembler 增加 thought 事件
2. 全栈: GeneratedPRD 加 workspace_id 字段 + 迁移
3. 全栈: DataStore 加 list_prds_by_workspace / get_prd_by_id
4. 全栈: pm.py 新增 `/pm/prd/by-id/{id}` + `/workspaces/{id}/prds` 端点
5. 全栈: PrdView.vue 改造（按 prd_id 查看）
6. 全栈: 新增 PrdListView.vue + WorkspaceDetail 加 Tab
7. 全栈: ProposalListView 生成对话框改造（思考 + 实时预览）
8. **全栈: 修复左侧会话不显示 — pm_list_sessions 放开 analyst/admin 看工作空间所有会话**
9. Evaluate: 端到端验证

---

## 8. Bug 修复：左侧工作空间会话不显示

### 根因
`app/api/pm.py:81` — `pm_list_sessions` 非 admin 用户只能看自己的 sessions：
```python
uid = current_user["id"]  # 只看自己创建的
sessions = [s for s in sessions if s.get("user_id") == uid]
```

新用户（analyst1/reviewer1/biz1）没创建过 session → 左侧栏工作空间展开后是空的。

### 修复方案
放开 `analyst`/`admin` 角色——可以看到工作空间内所有人的会话（业务需要：分析师要审核所有人的需求）：

```python
@router.get("/pm/sessions")
async def pm_list_sessions(
    current_user: dict = Depends(get_current_user),
    workspace_id: str | None = Query(default=None),  # 新增：按工作空间过滤
    all: bool = Query(default=False),
    ...
):
    role = current_user.get("role")
    if all and role != "admin":
        raise HTTPException(403, "仅管理员可查看所有会话")
    if all:
        uid = None
    elif role in ("analyst", "admin"):
        uid = None  # analyst/admin 能看所有会话（工作空间共享）
    else:
        uid = current_user["id"]  # business/reviewer 只看自己的

    sessions = await _svc().list_sessions()
    if uid:
        sessions = [s for s in sessions if s.get("user_id") == uid]
    if workspace_id:
        sessions = [s for s in sessions if s.get("workspace_id") == workspace_id]
    ...
```

### 前端适配
`session.ts` 的 `load()` 不变，但现在 analyst/admin 能拿到所有 sessions，左侧栏就能正确显示了。

### 验收
- [ ] analyst1 登录后左侧栏能看到所有工作空间的会话
- [ ] biz1（business）仍只看自己的会话
- [ ] admin 看所有
