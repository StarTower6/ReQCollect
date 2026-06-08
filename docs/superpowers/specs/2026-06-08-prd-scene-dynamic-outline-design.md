# PRD 场景化动态大纲设计文档

## 概述

将 PRD 生成管线从固定 9 章模板升级为**根据需求画像动态识别项目场景 → 生成匹配的大纲**。场景识别基于画像字段关键词匹配，不额外调用 LLM，不影响现有的 SSE 事件流和前端的兼容性。

## 架构

```
Planner（当前）                  Planner（升级后）
┌─────────────────────┐         ┌──────────────────────────────┐
│ PRD_SECTION_ORDER   │         │ SceneRecognizer              │
│ (固定 9 章)          │   →    │   recognize(profile) → scene │
│ plan() → sections []│         │ SectionSelector              │
└─────────────────────┘         │   select(scene, profile)     │
                                │   → sections[]（动态列表）    │
                                └──────────────────────────────┘
                                       │
                                        ↓  sections list（格式不变）
                                ┌──────────────────────────────┐
                                │ Assembler / Generator        │
                                │ （无需改动）                    │
                                └──────────────────────────────┘
```

## SceneRecognizer — 场景识别

### 识别逻辑（基于画像字段的规则匹配）

| 场景 | 判定条件（优先级序） |
|------|-------------------|
| **系统改造** | `existing_systems` 非空 且 (`business_background` / `current_process` 含"优化/升级/改造/替换/二期/迭代/重构") |
| **报表/BI 看板** | `functional_requirements` 含"报表/看板/统计/仪表盘/BI/大屏/驾驶舱" 且不含明显业务流程 |
| **审批流系统** | `business_flow` 含"审批/审核/复核/会签/签批" 且 `user_roles` 有 ≥3 个角色 |
| **数据治理项目** | `data_scale` 非空 且 (`business_background` 含"数据质量/数据标准/数据迁移/数据治理/数据清洗") |
| **接口集成项目** | `existing_systems` 非空且长度 ≥2，且 `functional_requirements` 不含明显界面功能 |
| **简单工具类** | `user_roles` ≤2 个角色，`functional_requirements` ≤3 项功能，且没有系统对接 |
| **默认（新建系统）** | 以上都不匹配，走全量 9 章 |

### 场景→章节选择

| 场景 | 包含章节 | 权重覆盖 |
|------|---------|---------|
| **新建系统** | 全量 9 章 | 全部 NORMAL |
| **系统改造** | 9 章（调整权重） | `system_integration`=HEAVY（加迁移过渡）, `constraints`=HEAVY（加变更风险）, `data_requirements`=LIGHT |
| **报表/BI 看板** | 7 章（去掉 business_flow, constraints） | `user_roles`=HEAVY（谁看什么报表）, `data_requirements`=HEAVY（数据来源+口径+更新频率）, `functional_requirements`=HEAVY（报表维度+钻取） |
| **审批流系统** | 8 章（去掉 data_requirements） | `business_flow`=HEAVY（加异常流程+驳回重审+超时处理）, `user_roles`=HEAVY（审批矩阵） |
| **数据治理项目** | 6 章（去掉 business_flow, non_functional, user_roles 轻量） | `data_requirements` 提到第 2 位, 额外加"数据质量规则"章节 |
| **接口集成项目** | 5 章（精简版） | `existing_systems`=HEAVY, `functional_requirements` 聚焦接口功能 |
| **简单工具类** | 5 章（project_overview, user_roles, functional_requirements, constraints, acceptance） | 全部 LIGHT |

### 权重对 prompt 的影响

- **LIGHT**: 在原 prompt 后追加 `注意：请精简描述，控制在 200 字以内`
- **NORMAL**: 使用默认 prompt
- **HEAVY**: 在原 prompt 后追加额外的深度要求（如在系统改造场景的 system_integration 中追加 `重点描述新旧系统过渡方案和数据迁移策略`）

## 改动清单

| 文件 | 改动 |
|------|------|
| `app/agent/pm/planner.py` | 重写：新增 `SceneRecognizer` 类 + `SceneType` 枚举 + `_get_scene_prompt()` 方法；`plan()` 方法签名不变 |
| `app/agent/pm/prompts.py` | 新增 `PRD_SCENE_PROMPT_OVERRIDES` 字典（场景×章节的 HEAVY/LIGHT prompt 覆盖），保留 `PRD_SECTION_TEMPLATES` |
| `app/agent/pm/state.py` | 无需改动 |
| `app/agent/pm/phase2/generator.py` | 无需改动 |
| `app/agent/pm/phase2/assembler.py` | 无需改动 |
| `app/services/pm_agent_service.py` | 无需改动 |
| `app/api/pm.py` | 无需改动 |

## 验收标准

- [x] P0: AI 自动从画像判断场景类型，不依赖用户手动选择
- [x] P0: 不同场景生成不同的章节列表（场景≈章节组合）
- [x] P0: 场景识别仅用规则匹配，不调用 LLM
- [x] P0: SSE 事件格式完全不变，前端无需改动
- [x] P0: `plan()` 签名不变，service/assembler 无需改动
- [x] P1: 7 种场景覆盖（新建/改造/报表/审批/数据/接口/简单工具）
- [x] P1: 场景识别可扩展（新增场景只需修改场景配置字典 + 条件函数）
