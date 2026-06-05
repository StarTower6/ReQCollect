"""Business requirement analyst persona prompt and PRD template."""

from textwrap import dedent

PM_SYSTEM_PROMPT = dedent("""
你是一位资深的企业IT需求分析师，在大型制造业信息化领域有10年以上经验。
你的工作是和业务部门的同事自然对话，帮他们把模糊的业务需求梳理清楚，
输出可供IT开发团队直接落地的需求文档。

## 你的工作流程

1. **了解业务背景** — 这个业务现状如何？在什么场景下？遇到了什么问题？
2. **逐步深入** — 现状流程 → 使用角色 → 核心业务流程 → 功能需求 → 系统对接 → 非功能需求 → 约束条件
3. **主动引导** — 当用户描述模糊时，用具体的选项引导。例如：
   「目前的审批是走纸质还是OA系统？」而不是「目前怎么审批的？」
4. **实时记录** — 用 `update_requirement_profile` 工具将每一步挖掘到的信息保存到需求画像
5. **自检覆盖** — 用 `get_profile_summary` 检查已覆盖和缺失的字段
6. **评估完整度** — 用 `evaluate_sufficiency` 评估需求完整度

## 对话原则

- 每次只问1-2个问题，不要一次问太多
- 用具体选项引导，不要开放式提问
- 每个问题必须包含2-4个可直接点击的选项，格式如下：
  【单选】提问内容
  A. 选项一
  B. 选项二
  C. 选项三
  D. 不确定/您觉得怎样更合适？
- 如果一次问两个问题，用两个独立的编号块，每个带【单选】/【多选】标签
- 先总结已经了解到的信息，再问下一个问题
- 当完整度达到75%时，主动建议生成需求文档
- 关注业务现状而非产品定位，关注当前痛点而非市场机会

## 语气

专业但友好。你是帮助业务部门梳理需求的信息化顾问，不是审讯官。
使用中文交流。

## 引导问题示例

- 「现在这个业务是手工跑还是有系统在支撑？」
- 「这个流程涉及哪些角色？大概各有多少人？」
- 「跟公司现有的哪些系统要打通？比如用友ERP、OA、MES？」
- 「每天大概会产生多少数据？多少人同时操作？」
- 「有没有合规要求？比如财务审计、数据安全？」
- 「工期和预算有什么限制？」
""").strip()

PRD_SECTION_TEMPLATES = {
    "project_overview": {
        "title": "1. 项目背景与目标",
        "prompt": dedent("""
            根据下面的需求画像，编写"项目背景与目标"章节。
            包括：业务现状、痛点分析、项目目标、项目范围（做什么/不做什么）。

            Profile:
            {profile_context}
        """).strip(),
    },
    "user_roles": {
        "title": "2. 用户角色与用例",
        "prompt": dedent("""
            编写"用户角色与用例"章节。对每个角色，描述其职责、操作场景、权限需求。
            包含一张角色-权限矩阵表。

            Profile:
            {profile_context}
        """).strip(),
    },
    "business_flow": {
        "title": "3. 业务流程",
        "prompt": dedent("""
            编写"业务流程"章节。描述核心业务链路：主流程、分支流程、异常处理。
            包含流程步骤描述。

            Profile:
            {profile_context}
        """).strip(),
    },
    "functional_requirements": {
        "title": "4. 功能需求",
        "prompt": dedent("""
            编写"功能需求"章节。按模块列出具体功能，标注优先级（P0/P1），
            每个功能包含详细描述和验收条件。

            Profile:
            {profile_context}
        """).strip(),
    },
    "system_integration": {
        "title": "5. 系统集成",
        "prompt": dedent("""
            编写"系统集成"章节。列出需要对接的现有系统清单，
            说明集成方式（API/文件/数据库直连）、数据流向、接口规范。

            Profile:
            {profile_context}
        """).strip(),
    },
    "non_functional": {
        "title": "6. 非功能需求",
        "prompt": dedent("""
            编写"非功能需求"章节。覆盖：性能指标、并发量、安全性、
            合规要求、可用性、数据备份与恢复。

            Profile:
            {profile_context}
        """).strip(),
    },
    "data_requirements": {
        "title": "7. 数据需求",
        "prompt": dedent("""
            编写"数据需求"章节。包括：数据量预估、存储要求、
            数据归档策略、报表需求、数据字典概览。

            Profile:
            {profile_context}
        """).strip(),
    },
    "constraints": {
        "title": "8. 实施约束与风险",
        "prompt": dedent("""
            编写"实施约束与风险"章节。列出：工期限制、预算约束、
            技术路线约束、依赖项、潜在风险与应对措施。

            Profile:
            {profile_context}
        """).strip(),
    },
    "acceptance": {
        "title": "9. 验收标准",
        "prompt": dedent("""
            编写"验收标准"章节。针对每个功能模块编写可量化的验收条件，
            明确验收流程和交付物清单。

            Profile:
            {profile_context}
        """).strip(),
    },
}

PRD_SECTION_ORDER = [
    "project_overview",
    "user_roles",
    "business_flow",
    "functional_requirements",
    "system_integration",
    "non_functional",
    "data_requirements",
    "constraints",
    "acceptance",
]
