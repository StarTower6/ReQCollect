# 08 — 工作空间与需求图谱

## 概述

当前 ReQCollect 的所有会话和需求是扁平的，通过 `project_name` 字段标识归属项目。本模块将"项目"提升为**一级实体——工作空间（Workspace）**，并在工作空间内建立需求 Wiki 体系与需求知识图谱，实现企业级的多项目管理、知识沉淀与需求关系可视化。

### 核心能力

```
工作空间（项目级组织单元）
  ├── 人员管理（角色权限体系）
  ├── 对话 Session（挖需求）
  │   └── 需求条目 → 关联 Wiki 页面
  ├── Wiki 文库（需求详情 / 决策记录 / 知识沉淀）
  │   └── [[Wikilink]] 页面间链接
  └── 需求图谱（Graph View）
        └── 节点 = Wiki 页面
        └── 边 = 页面间的引用/依赖关系
```

### 参考来源

本模块的 Wiki 和图谱设计参考了 **Trilium Notes**（https://github.com/zadam/trilium）：
- 实体分离架构：笔记（BNote）↔ 树形结构（BBranch）↔ 属性/关系（BAttribute）
- `[[链接]]` 语法 + 自动反向索引
- Note Map 力导向图谱渲染

---

## 一、工作空间管理

### 1.1 业务场景

PM 同时管理多个项目（如 MES 系统升级、ERP 采购模块改造、质量追溯平台建设），每个项目需要：
- 独立的项目空间，需求不相互干扰
- 不同的项目成员访问不同的项目
- 项目内有自己的会话记录、Wiki 文库和需求图谱

### 1.2 功能需求

#### P0 — 工作空间 CRUD

| # | 需求 | 验收标准 |
|---|------|----------|
| 1.1 | **创建工作空间** | 提供「新建项目」入口，输入项目名称（必填）、项目描述（选填）、项目编码（选填，如 MES-2026），创建后进入该工作空间 |
| 1.2 | **工作空间列表** | 主页展示当前用户可访问的所有工作空间卡片（项目名称、描述、成员数、需求数、最近更新时间） |
| 1.3 | **工作空间详情页** | 进入工作空间后展示：项目概览、成员列表、会话列表、Wiki 文库入口、图谱入口 |
| 1.4 | **编辑工作空间** | 项目管理员可修改项目名称、描述、编码 |
| 1.5 | **删除工作空间** | 项目管理员可删除工作空间——删除前确认（弹窗提示将级联删除所有会话、需求、Wiki 页面和图谱关系） |

#### P0 — 工作空间与 Session 的关联

| # | 需求 | 验收标准 |
|---|------|----------|
| 2.1 | **在工作空间中创建 Session** | 进入工作空间后，点击「新建会话」即在该工作空间下创建 session；现有会话新建流程改为：先选/创建工作空间 → 再创建会话 |
| 2.2 | **Session 隶属工作空间** | `sessions` 表新增 `workspace_id` 字段关联工作空间，删除 `project_name` 字段（数据迁移：将现有 session 的 project_name 自动创建为对应工作空间） |
| 2.3 | **工作空间内查看会话** | 工作空间的会话列表仅展示属于该空间的会话，支持按日期/完整度排序 |
| 2.4 | **跨工作空间隔离** | A 工作空间的会话、需求、Wiki 内容对非成员不可见 |

#### P0 — 数据迁移

| # | 需求 | 验收标准 |
|---|------|----------|
| 3.1 | **现有数据迁移** | 系统升级时，对所有 session 的 `project_name` 做 DISTINCT，自动为每个项目名创建一个工作空间，所有同名 session 归入该空间 |
| 3.2 | **迁移提示** | 升级后管理员看到「已从现有数据自动创建 N 个工作空间」提示，可在工作空间管理页面补充描述和成员 |

---

## 二、工作空间人员管理

### 2.1 业务场景

一个 ERP 采购项目：张工（项目经理）负责总体把控，李工（需求分析员）负责挖需，王工（业务骨干）参与需求评审，赵工（IT 架构师）查看技术方案。不同角色对工作空间有不同的操作权限。

### 2.2 角色定义

| 角色 | 权限范围 |
|------|---------|
| **项目管理员**（project_admin） | 修改/删除工作空间；添加/移除成员；修改成员角色；访问所有会话、Wiki、图谱 |
| **需求编辑者**（requirement_editor） | 创建/编辑会话；创建/编辑 Wiki 页面；在对话中挖需求；生成 PRD |
| **PRD 审阅者**（prd_reviewer） | 查看所有会话和需求；查看/评论 PRD；不能新建会话和编辑 Wiki |
| **查看者**（viewer） | 只读访问：查看会话记录、Wiki 页面、图谱；不可作任何修改操作 |

> **与现有全局角色的关系**：全局角色（admin/analyst/reviewer/business）保持不变。工作空间角色在全局角色之上**叠加**——用户需要同时具备全局角色的基本访问权限（至少 `reviewer` 或以上）才能被添加到工作空间中。`admin` 全局角色自动拥有对所有工作空间的完全访问。

### 2.3 功能需求

#### P0 — 成员管理

| # | 需求 | 验收标准 |
|---|------|----------|
| 4.1 | **添加成员** | 项目管理员可通过用户名/邮箱搜索系统用户，添加到工作空间并分配角色 |
| 4.2 | **修改成员角色** | 项目管理员可随时修改成员的 workspace 角色 |
| 4.3 | **移除成员** | 项目管理员可将成员从工作空间移除，移除后该成员不可再访问该空间的内容 |
| 4.4 | **成员列表** | 工作空间详情页展示所有成员及其角色、加入时间；按角色分组显示 |
| 4.5 | **权限校验** | 后端 API 每个接口校验：请求用户是否在工作空间成员中 + 是否具备操作所需角色 |

#### P1 — 邀请流程

| # | 需求 | 验收标准 |
|---|------|----------|
| 5.1 | **邀请链接** | 项目管理员可生成工作空间邀请链接（带有效期，24 小时），发送给未注册用户 |
| 5.2 | **申请加入** | 普通用户可看到工作空间列表中的"申请加入"按钮（需管理员审批） |

#### P2 — 角色模板

| # | 需求 | 验收标准 |
|---|------|----------|
| 6.1 | **预定义角色模板** | 提供"标准开发项目"、"需求调研项目"等角色模板，一键配置角色体系 |
| 6.2 | **自定义角色** | 项目管理员可创建自定义角色并分配具体权限集（细粒度到按钮级别） |

---

## 三、需求 Wiki

### 3.1 业务场景

在对话中挖出的"采购订单审批流程优化"需求，背后需要补充：
- 当前审批流程的详细描述（流程图、节点角色）
- 与 SAP 接口的对接方式
- 业务方提出的特殊约束条件
- 与"采购订单自动生成"需求的关联关系

这些内容不适合在对话会话中反复讨论，而是需要一个**独立的 Wiki 页面**来沉淀，并且可以在页面间建立引用关系。

### 3.2 Wiki 页面的生命周期

```
对话 Session 中挖出需求条目
       ↓
LLM 自动生成 Wiki 页面（初始版本）
       ↓
人工修改 / 补充 Wiki 内容
       ↓
在 Wiki 中添加 [[链接]] 引用其他需求
       ↓
图谱自动更新 → 需求关系可视化
```

### 3.3 功能需求

#### P0 — 需求 Wiki 页面管理

| # | 需求 | 验收标准 |
|---|------|----------|
| 7.1 | **自动创建 Wiki 页面** | 在对话 session 中，AI 确认一条需求后（需求完整度达到单条阈值或 session 结束批量生成），自动在该工作空间下创建一个 Wiki 页面，标题 = 需求名称 |
| 7.2 | **查看 Wiki 页面** | 每个需求条目旁显示「📄 查看 Wiki」链接，点击打开该需求对应的 Wiki 页面 |
| 7.3 | **编辑 Wiki 页面** | 支持 Markdown 编辑器编辑 Wiki 内容，实时保存（或手动保存按钮），语法高亮 + 预览双栏模式 |
| 7.4 | **Wiki 页面列表** | 工作空间内提供「Wiki 文库」入口，以列表展示所有 Wiki 页面（标题、创建时间、最后编辑者、关联需求数） |
| 7.5 | **删除 Wiki 页面** | 需求编辑者可删除 Wiki 页面（删除前确认，不影响 session 中的原始需求记录） |
| 7.6 | **Wiki 页面版本历史** | 每次编辑保存一个版本，支持查看历史版本和回滚（P1 可选） |

#### P0 — Wiki 页面内容结构

Wiki 页面默认包含以下 LLM 自动填充的章节（参考 Trilium 的 BAttribute 设计，用结构化字段而非硬编码）：

| 章节 | 内容 | 填充方式 |
|------|------|---------|
| **需求概述** | 需求的简要描述 + 提出人 + 提出时间 | LLM 从对话中提取 |
| **业务背景** | 为什么要做这个需求？当前有什么痛点？ | LLM 从对话中提取 |
| **功能描述** | 具体要实现什么功能 | LLM 从对话中提取 |
| **约束条件** | 技术约束、性能要求、合规要求 | LLM 从对话中提取 + 人工补充 |
| **关联系统** | 需要对接的现有系统（OA/ERP/SAP 等） | LLM 从对话中提取 + `[[链接]]` 引用 |
| **关联需求** | 引用其他需求的 Wiki 页面 | `[[需求名称]]` 手工添加或 LLM 建议 |
| **决策记录** | 讨论中做出的关键决策及原因 | LLM 从对话中提取 + 人工审核 |
| **验收标准** | 该需求如何验证 | LLM 从对话中提取 + 人工完善 |

#### P0 — 手工创建 Wiki 页面

| # | 需求 | 验收标准 |
|---|------|----------|
| 8.1 | **新建空白 Wiki 页** | 需求编辑者可在 Wiki 文库中直接创建空白 Wiki 页面，标题自定，手动填写内容 |
| 8.2 | **手动关联需求** | 空白 Wiki 页面可关联到工作空间中的某个需求条目（下拉选择），也可不关联（作为通用知识页面） |
| 8.3 | **知识沉淀** | Wiki 页面支持不关联需求，作为工作空间的通用知识库页面（如项目约定、API 文档、架构决策记录 ADR） |

#### P1 — LLM 增强 Wiki

| # | 需求 | 验收标准 |
|---|------|----------|
| 9.1 | **AI 建议补充** | Wiki 页面编辑时，AI 自动检测内容缺失章节，在底部浮窗提示「AI 建议补充 XX 内容」，一键生成 |
| 9.2 | **AI 提炼对话** | 当 Wiki 页面关联某 session 时，AI 可提取该 session 中与该需求相关的对话片段，追加到 Wiki |
| 9.3 | **AI 链接建议** | 编辑 Wiki 时，AI 根据内容自动推荐可能关联的其他 Wiki 页面，一键插入 `[[链接]]` |

---

## 四、Wiki 链接系统

### 4.1 设计参考（Trilium）

Trilium 的 BAttribute 用统一的 `type: "label" | "relation"` 来处理元数据和引用关系。其中 `relation` 类型就是 `[[链接]]` 的存储形式：

```
BAttribute {
  type: "relation"
  name: "internalLink"      // 链接类型（或自定义"dependsOn"）
  value: "目标页面的 ID"    // 指向的目标 Wiki 页面
}
```

反向索引通过 `targetNote.targetRelations.push(this)` 自动建立。

### 4.2 功能需求

#### P0 — 链接语法与解析

| # | 需求 | 验收标准 |
|---|------|----------|
| 10.1 | **[[链接]] 语法** | 在 Wiki 编辑器中使用 `[[需求名称]]` 或 `[[页面标题]]` 创建链接，保存时自动解析并建立关系 |
| 10.2 | **自动补全** | 输入 `[[` 时弹出下拉框，搜索当前工作空间内的所有 Wiki 页面标题，选择后自动补全 |
| 10.3 | **点击跳转** | 在渲染后的 Wiki 页面中，`[[链接]]` 显示为可点击的内部链接，点击跳转到目标 Wiki 页面 |
| 10.4 | **悬停预览** | 鼠标悬停在 `[[链接]]` 上时，浮窗显示目标页面的摘要（前 100 字） |

#### P0 — 关系存储

| # | 需求 | 验收标准 |
|---|------|----------|
| 11.1 | **关系表存储** | 新增 `wiki_links` 表存储页面间关系，保存 `source_page_id` → `target_page_id` 的有向边 |
| 11.2 | **自动反向链接** | 当 A 页面链接到 B 页面时，B 页面的「反向链接」列表中自动出现 A 页面（类似 Obsidian 的反向链接面板） |
| 11.3 | **链接关系类型** | 支持在 `[[链接|类型]]` 中标注关系类型：`[[订单审批|依赖]]`、`[[库存查询|参考]]`、`[[SAP 接口|集成]]` 等 |
| 11.4 | **编辑时自动同步** | 编辑 Wiki 页面保存时，自动 diff 链接关系：新增的链接创建记录，删除的链接移除记录（参考 Trilium 的 `saveLinks()` 实现） |

#### P1 — 链接分析

| # | 需求 | 验收标准 |
|---|------|----------|
| 12.1 | **孤立页面检测** | 图谱工具中自动标注「无任何链接的孤立页面」，显示数量，便于 PM 发现未关联的需求 |
| 12.2 | **链接密度统计** | 显示工作空间的平均链接数、入链最多的页面（"核心需求"标识） |
| 12.3 | **断链检测** | 删除 Wiki 页面时，检查是否有其他页面链接到它，提示「将有 N 个页面产生断链」，提供批量更新选项 |

---

## 五、需求图谱（Graph View）

### 5.1 设计参考（Trilium）

Trilium 的 Note Map 提供两种图模式：
1. **Tree 模式** — 显示树形层级关系（父子边）
2. **Link 模式** — 仅显示用户定义的 relation 关系边

渲染使用 `force-graph` 库（Canvas 2D 力导向布局），后端通过 BFS 3 层扩展获取相关节点数据。

参考数据流：
```
前端触发 → API 请求（noteId, maxDepth=3）
  → 后端 BFS 遍历获取节点（去重）
  → 构建节点数组 + 边数组
  → 返回 JSON → force-graph 渲染
```

### 5.2 功能需求

#### P0 — 图谱展示

| # | 需求 | 验收标准 |
|---|------|----------|
| 13.1 | **图谱入口** | 工作空间的导航中显示「需求图谱」入口，点击进入全屏图谱视图 |
| 13.2 | **力导向布局** | 图谱使用力导向布局渲染，节点可拖拽移动，自动弹回稳定位置 |
| 13.3 | **节点 = Wiki 页面** | 每个 Wiki 页面为一个圆形节点，节点大小根据入链数量动态计算（入链越多越大） |
| 13.4 | **边 = 页面间链接** | 页面间的 `[[链接]]` 显示为有向边（带箭头），边的颜色按关系类型区分（依赖=红色，参考=蓝色，集成=绿色） |
| 13.5 | **节点信息浮窗** | 悬停或点击节点时显示浮窗：页面标题、摘要前 50 字、入链数/出链数 |
| 13.6 | **点击跳转** | 双击节点跳转到对应的 Wiki 页面 |
| 13.7 | **缩放与拖拽** | 图谱支持鼠标滚轮缩放、拖拽平移、框选节点 |

#### P0 — 图谱数据

| # | 需求 | 验收标准 |
|---|------|----------|
| 14.1 | **工作空间级图谱** | 图谱默认展示当前工作空间下所有 Wiki 页面及其关系（同 Obsidian 的 "Global Graph"） |
| 14.2 | **局部聚焦** | 在 Wiki 页面内提供「在此页面的局部图谱中查看」按钮，仅展示该页面及其直接关联的页面（同 Obsidian 的 "Local Graph"） |
| 14.3 | **后台数据计算** | 后端实时计算图数据：节点 = workspace_id 下的所有 Wiki 页面；边 = wiki_links 表中属于这些页面的所有关系；返回 JSON 格式 `{ nodes: [...], links: [...] }` |

#### P1 — 图谱交互增强

| # | 需求 | 验收标准 |
|---|------|----------|
| 15.1 | **筛选过滤** | 图谱侧栏提供筛选面板：按关系类型过滤边（仅显示"依赖"关系）、按标签过滤节点（仅显示 P0 需求） |
| 15.2 | **搜索节点** | 图谱中提供搜索框，输入关键词高亮匹配的节点，自动聚焦到该节点 |
| 15.3 | **导出图谱** | 支持截图导出（PNG）或数据导出（JSON），用于汇报展示 |
| 15.4 | **节点分组** | 支持按标签/模块将节点用色块分组（类似 Obsidian 的 group） |
| 15.5 | **动画** | 图谱加载时播放节点弹入动画，拖拽时有缓动效果 |

---

## 六、LLM + Wiki 自动生成

### 6.1 业务场景

PM 在对话 session 中挖出需求后，不希望手动为每条需求写 Wiki 页面。AI 应该自动完成：

1. 从对话历史中提取相关内容
2. 生成结构化的 Wiki 页面
3. 自动识别并建立页面间的 `[[链接]]`
4. PM 只需审核 + 微调

### 6.2 功能需求

#### P0 — 自动生成

| # | 需求 | 验收标准 |
|---|------|----------|
| 16.1 | **Session 结束时批量生成** | 当 session 达到完整度阈值并生成了 PRD 后，自动为每条需求创建一个 Wiki 页面，填充所有可提取的章节 |
| 16.2 | **单条需求确认时生成** | 或在对话中确认某条需求的完整性后立即生成该条需求的 Wiki 页面（用户可选偏好） |
| 16.3 | **AI 检测关联** | 生成 Wiki 时，AI 自动检测该需求是否与工作空间内已有 Wiki 页面相关，自动插入 `[[引用]]` |
| 16.4 | **生成预览** | 生成 Wiki 后不直接保存，先展示预览给 PM，PM 确认后再保存入库（可配置是否需要确认） |

#### P1 — 增量更新

| # | 需求 | 验收标准 |
|---|------|----------|
| 17.1 | **AI 补充内容** | 在已有 Wiki 页面中点「AI 补充」，AI 根据该需求在后续 session 中的讨论内容，更新 Wiki 的对应章节 |
| 17.2 | **自动链接建议** | 每次生成新的 Wiki 页面时，AI 提示「检测到可能与以下页面存在关联」，建议 PM 确认链接 |
| 17.3 | **图谱标注** | 图谱中 AI 自动标识「建议链接」的灰色虚线边，PM 确认后转为实边 |

---

## 七、UI 交互设计

### 7.1 布局设计

基于现有原生 HTML/CSS/JS 单页扩展：

```
┌─────────────────────────────────────────────────┐
│  [ReQCollect]  工作空间: ERP 采购模块改造     │ ← 顶栏（工作空间名称 + 导航）
│  主页 │ 对话 │ Wiki文库 │ 需求图谱 │ 成员管理  │ ← 导航标签
├─────────────────────────────────────────────────┤
│                                                 │
│                主内容区域                        │
│          (按当前导航切换内容)                    │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 7.2 页面路径

| 页面 | URL 路径 | 说明 |
|------|---------|------|
| 工作空间列表 | `/` | 展示所有可访问工作空间卡片 |
| 工作空间首页 | `/workspace/{id}` | 项目概览、快速入口 |
| 对话列表 | `/workspace/{id}/sessions` | 该空间下所有会话 |
| 对话 | `/workspace/{id}/sessions/{sid}` | 对话聊天界面 |
| Wiki 文库 | `/workspace/{id}/wiki` | Wiki 页面列表 |
| Wiki 详情 | `/workspace/{id}/wiki/{page_id}` | Wiki 页面详情（渲染/编辑模式） |
| 需求图谱 | `/workspace/{id}/graph` | 全屏图谱视图 |
| 成员管理 | `/workspace/{id}/members` | 成员列表与权限管理 |

### 7.3 Wiki 编辑器

Wiki 页面提供两种模式切换：

| 模式 | 显示 |
|------|------|
| **视图模式**（默认） | Markdown 渲染后的富文本展示，`[[链接]]` 可点击跳转，显示反向链接面板 |
| **编辑模式** | 分栏布局：左侧编辑区（Markdown 源码） + 右侧预览区（实时渲染）|

编辑区下方显示：
- 「AI 补充」按钮
- 「保存」按钮（Ctrl+S 快捷键）
- 「版本历史」链接（P1）

### 7.4 图谱页面

| 元素 | 说明 |
|------|------|
| **画布** | 全屏 Canvas 力导向图谱 |
| **侧栏** | 节点列表 + 筛选条件（关系类型/标签/关键词搜索） |
| **浮窗** | 悬停/点击节点显示摘要信息 + 「查看 Wiki」按钮 |
| **底部** | 统计信息：节点数、边数、孤立节点数 |

---

## 八、数据模型设计（新增）

### 8.1 新增表

```sql
-- ============================================
-- 工作空间（Workspace）
-- ============================================
CREATE TABLE workspaces (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,          -- 项目名称
    code          VARCHAR(100),                   -- 项目编码（如 MES-2026）
    description   TEXT,                           -- 项目描述
    created_by    VARCHAR(100) NOT NULL,           -- 创建者用户名
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_created_by (created_by)
);

-- ============================================
-- 工作空间成员（Workspace Members）
-- 参考：Trilium 没有独立成员表（它没有多用户），
-- 此为 ReQCollect 自有设计
-- ============================================
CREATE TABLE workspace_members (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    workspace_id    INT NOT NULL,
    user_id         VARCHAR(100) NOT NULL,        -- 用户 ID（关联 users 表）
    role            ENUM('project_admin','requirement_editor','prd_reviewer','viewer') NOT NULL DEFAULT 'viewer',
    joined_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_workspace_user (workspace_id, user_id)
);

-- ============================================
-- 会话增加 workspace_id 字段（修改已有表）
-- ALTER TABLE sessions ADD COLUMN workspace_id INT;
-- ============================================

-- ============================================
-- Wiki 页面（Wiki Pages）
-- 参考：Trilium 的 BNote + BBranch 分离设计
-- 简化版：BNote（页面内容）+ parent_id（层级树）
-- ============================================
CREATE TABLE wiki_pages (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    workspace_id    INT NOT NULL,                 -- 所属工作空间
    parent_id       INT DEFAULT NULL,             -- 父页面 ID（层级树，NULL=根级）
    requirement_id  INT DEFAULT NULL,             -- 关联的需求条目 ID（可为 NULL，用于纯知识页面）
    title           VARCHAR(255) NOT NULL,        -- 页面标题
    content         LONGTEXT,                     -- Markdown 内容
    content_html    LONGTEXT,                     -- 渲染后的 HTML（缓存）
    sort_order      INT DEFAULT 0,                -- 同层排序
    created_by      VARCHAR(100) NOT NULL,
    updated_by      VARCHAR(100),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES wiki_pages(id) ON DELETE SET NULL,
    INDEX idx_workspace (workspace_id),
    INDEX idx_requirement (requirement_id)
);

-- ============================================
-- Wiki 页面版本历史（Wiki Page Revisions）
-- 参考：Trilium 的 BRevision
-- ============================================
CREATE TABLE wiki_page_revisions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    page_id         INT NOT NULL,
    title           VARCHAR(255) NOT NULL,
    content         LONGTEXT,
    edited_by       VARCHAR(100) NOT NULL,
    revision_num    INT NOT NULL,                  -- 版本号
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
    INDEX idx_page (page_id)
);

-- ============================================
-- Wiki 页面链接（Wiki Links）
-- 参考：Trilium 的 BAttribute (type="relation")
-- 存储 [[链接]] 的有向边
-- ============================================
CREATE TABLE wiki_links (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    source_page_id      INT NOT NULL,             -- 链接发出的页面
    target_page_id      INT NOT NULL,             -- 链接指向的页面
    link_type           VARCHAR(50) DEFAULT 'reference',  -- 链接类型：reference, dependency, integration, etc.
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
    FOREIGN KEY (target_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
    UNIQUE KEY uk_link (source_page_id, target_page_id),
    INDEX idx_source (source_page_id),
    INDEX idx_target (target_page_id)
);

-- ============================================
-- Wiki 页面标签（Wiki Page Labels）
-- 参考：Trilium 的 BAttribute (type="label")
-- ============================================
CREATE TABLE wiki_labels (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    page_id         INT NOT NULL,
    name            VARCHAR(100) NOT NULL,         -- 标签名
    value           VARCHAR(255) DEFAULT '',       -- 标签值（支持 key=value）
    is_inheritable  BOOLEAN DEFAULT FALSE,         -- 是否沿层级树继承
    FOREIGN KEY (page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
    INDEX idx_page (page_id)
);
```

### 8.2 现有表修改

```sql
-- sessions 表增加 workspace_id
ALTER TABLE sessions ADD COLUMN workspace_id INT AFTER id;
ALTER TABLE sessions ADD INDEX idx_workspace (workspace_id);

-- （可选）删除 sessions 表的 project_name 字段
-- ALTER TABLE sessions DROP COLUMN project_name;
-- 注意：删除前确认数据迁移已完成
```

### 8.3 与现有模块的关系

| 现有模块 | 影响 |
|---------|------|
| 01-对话挖需引擎 | Session 必须在工作空间下创建；新增需求后自动生成 Wiki 页面 |
| 02-PRD生成管线 | PRD 生成时引用关联的 Wiki 内容作为背景知识 |
| 03-用户与权限 | 新增工作空间级角色，与全局角色叠加生效 |
| 04-存储与数据 | 新增 6 张表，修改 sessions 表 |
| 06-前端界面 | 重构入口页（工作空间列表取代扁平导航），新增 Wiki 编辑器、图谱页面、成员管理页面 |
| 07-导入与知识库 | 导入的文档内容可以关联到 Wiki 页面 |

---

## 九、技术约束

### 9.1 前端

- **图谱渲染库**：推荐使用 `force-graph`（基于 Three.js/Canvas 2D）或 `vis-network`，纯 JS 库，不依赖 Vue/React 等框架
- **Markdown 编辑器**：推荐 `SimpleMDE` 或 `EasyMDE`（基于 CodeMirror），支持分栏预览
- **链接解析**：自定义 `[[链接]]` 正则解析器，在保存时检测并更新 wiki_links 表
- **所有 UI 在现有原生 HTML/CSS/JS 单页上扩展**，不加构建工具

### 9.2 后端

- Wiki 页面内容存 Markdown（`LONGTEXT`），渲染后的 HTML 缓存字段 (`content_html`) 在保存时自动更新
- 图谱 API 实时计算（遍历 workspace_id 下的 wiki_pages + wiki_links），数据量较小时无需预计算
- 链接解析在 `Wiki 页面保存` 的后端服务中完成，使用正则匹配 `\[\[([^\|]+)(?:\|([^\]]+))?\]\]` 提取所有链接

### 9.3 性能考虑

- 单个工作空间 Wiki 页面 ≤ 500 页时，图谱实时计算无压力（需验证 force-graph 在 500 节点下的性能）
- 超过 500 页需考虑：后端缓存图数据（按 workspace_id 做 Redis 缓存）、前端做节点 LOD（Level of Detail）裁剪
- `wiki_pages.content` 使用 LONGTEXT（MySQL 最大 4GB），单个页面建议 ≤ 1MB

---

## 十、验收总表

### P0（核心 MVP）

- [ ] 工作空间 CRUD（创建/列表/编辑/删除）
- [ ] 会话从属于工作空间（新建时选工作空间）
- [ ] 现有 session 数据迁移（project_name → workspace）
- [ ] 工作空间成员管理（添加/移除/角色分配）
- [ ] 4 种工作空间角色权限校验（project_admin / requirement_editor / prd_reviewer / viewer）
- [ ] Session 结束后自动为需求生成 Wiki 页面
- [ ] Wiki 页面查看与 Markdown 编辑
- [ ] Wiki 页面列表（按工作空间隔离）
- [ ] `[[链接]]` 语法解析与自动补全
- [ ] wiki_links 表存储页面间关系
- [ ] 反向链接自动索引
- [ ] 力导向图谱展示（节点=Wiki页面，边=页面链接）
- [ ] 工作空间级全局图谱
- [ ] 局部图谱（单页面及其直接关联）

### P1（迭代增强）

- [ ] Wiki 页面版本历史与回滚
- [ ] AI 建议补充内容 / AI 提炼对话记录到 Wiki
- [ ] AI 链接建议（生成时自动推荐关联页面）
- [ ] 邀请链接 + 申请加入工作空间
- [ ] 链接关系类型标注（依赖/参考/集成）
- [ ] 孤立页面检测 / 断链处理提示
- [ ] 图谱筛选过滤（按关系类型/标签）
- [ ] 图谱搜索节点
- [ ] 图谱截图导出

### P2（远期）

- [ ] 角色模板（预定义角色体系）
- [ ] 自定义角色（精细权限配置）
- [ ] 节点分组（按标签色块）
- [ ] AI 自动标注「建议链接」的图谱虚线边
- [ ] 链接密度统计 / 核心需求标识
- [ ] 图谱加载动画与交互优化

---

## 十一、开放问题

| # | 问题 | 决议 |
|---|------|------|
| 1 | Wiki 页面树形层级：是否支持子页面嵌套（如"ERP"→"采购模块"→"订单审批"）？ | 表中预留 `parent_id` 字段，一期先做扁平列表，二期启用层级 |
| 2 | 链接关系类型：预定义哪些类型？ | `reference`（参考）、`dependency`（依赖）、`integration`（集成），可在 UI 中自定义 |
| 3 | Wiki 页面是否支持图片附件/文件上传？ | 一期只支持 Markdown 文字，图片通过外部链接嵌入，二期支持附件 |
| 4 | 图谱可视化库选型？ | 推荐 `vis-network`（文档完善、纯 JS、无需 WebGL）或 `force-graph`（性能更好、支持 Canvas/WebGL） |
| 5 | workspace_code 的编码规则？ | 项目管理员自由填写，不强制格式；可作为 URL 中 workspace 的友好标识 |

---

> 版本：v1.0
> 参考项目：Trilium Notes (MIT license) — 数据模型（Note+Branch+Attribute 分离）、链接解析、图谱渲染设计
