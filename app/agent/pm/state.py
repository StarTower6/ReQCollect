"""PM Agent state definitions — business requirement focus."""

import operator
from typing import Annotated, TypedDict


class RequirementProfile(TypedDict, total=False):
    """Structured requirement profile — business requirement focus for manufacturing IT."""

    project_name: str                              # 项目名称
    business_background: str                       # 业务背景与痛点
    current_process: str                           # 当前流程/系统现状
    user_roles: list  # [{"role":"审批人","count":50,"dept":"财务部"}]
    business_flow: str                             # 核心业务流程描述
    functional_requirements: list  # [{"module":"报销录入","features":["...","..."],"priority":"P0"}]
    existing_systems: list  # ["用友ERP","OA系统","MES"]
    non_functional: dict  # {"performance":"...","security":"...","compliance":"..."}
    data_scale: str                               # 数据量与并发预期
    constraints: list[str]                        # 工期/预算/技术约束
    success_criteria: list[str]                   # 验收标准与期望效果

    covered_topics: list[str]
    pending_questions: list[str]
    sufficiency_score: float


class PMState(TypedDict):
    """Full PM Agent session state."""

    messages: Annotated[list, operator.add]
    profile: RequirementProfile
    phase: str  # "mining" | "generating" | "complete"
    generation_mode: str  # "one_shot" | "incremental"
    prd_sections: list  # [{"title": "...", "content": "...", "status": "pending|done"}]
    prd_markdown: str
