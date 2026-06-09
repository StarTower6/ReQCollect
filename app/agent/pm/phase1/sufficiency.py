"""Requirement completeness evaluator — v2 with scene-aware field weights.

Evaluates the requirement profile and generates probing questions.
Field weights shift dynamically based on detected project scene
(e.g. BI/report projects weight data_scale higher).
"""

import re

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.agent.pm.tools import get_profile, resolve_thread_id


class CompletenessResult(BaseModel):
    score: float = Field(description="Completeness score 0.0 to 1.0")
    missing_fields: list[str] = Field(description="Fields that still need to be filled")
    suggested_questions: list[str] = Field(description="Suggested questions to ask the user next")
    reasoning: str = Field(description="Brief reasoning for the score")


# ── Base weights (normalized, sum = 1.0) ──

_BASE_FIELD_RULES = [
    ("project_name", 0.05, "项目名称",
     "这个需求一般怎么称呼？你们内部有没有一个约定的项目名称？",
     "比如是叫\"财务报销系统\"还是\"费用管理平台\"？",
     "我先记下了——方便后面我们讨论时有个名字。"),

    ("business_background", 0.12, "业务背景与痛点",
     "目前这个业务是怎么跑的？遇到了什么问题导致想改变？",
     "能不能举一个具体例子？比如最近有没有因为流程问题影响工作的？",
     "所以我理解主要痛点是（重述）——对吗？还有没有其他类似的问题？"),

    ("current_process", 0.12, "现状流程",
     "现在是手工做还是有系统在跑？流程是从哪里到哪里的？",
     "整个流程大概经过几个人？通常要多久？有没有哪一步特别容易卡住？",
     "我整理一下，目前是这样的——（重述）——哪个环节你觉得最需要改进？"),

    ("user_roles", 0.15, "使用角色",
     "这个流程涉及哪些角色或部门？每个角色的职责是什么？",
     "比如财务部有多少人需要每天用到？部门经理通常多久操作一次？",
     "所以关键角色是（列举）——我有没有漏掉谁？"),

    ("business_flow", 0.10, "业务流程",
     "核心业务链路是怎样的？从开始到结束大致分几步？",
     "我拿一个场景举例：一个普通员工要发起一次流程，他第一步做什么？每一步的输入和输出是什么？",
     "我理解流程是 A→B→C。有没有什么特殊情况？比如（异常场景）？"),

    ("functional_requirements", 0.15, "功能需求",
     "业务你觉得系统最需要帮你解决哪几件事？",
     "在这几件事里，如果只能先做一件，你觉得哪个是绝对不能少的？",
     "所以核心功能是（列举）——优先级这样排，你觉得合理吗？"),

    ("existing_systems", 0.10, "系统对接",
     "这个业务跟公司现有的哪些系统有关系？比如用友 ERP、OA、MES？",
     "具体来说，哪些数据需要在两个系统之间流转？目前是怎么做的？",
     "所以需要对接的是（列举）——有没有遗漏？"),

    ("non_functional", 0.08, "质量与性能要求",
     "这些业务流程有没有什么质量、安全或合规方面的硬性要求？比如财务数据要满足审计规范？",
     "比如报销审批记录需要保存几年？大概多少人同时使用？",
     "所以主要关注点是（重述）——我有没有理解偏？"),

    ("data_scale", 0.05, "数据量级",
     "大概有多少人会用这个系统？每天会产生多少条数据？",
     "比如报销单一个月大概产生多少张？几年下来数据量会不会很大？",
     "数据主要还是文本和数字为主对吗？有没有图片、附件之类的？"),

    ("constraints", 0.05, "约束条件",
     "工期、预算方面有没有限制？公司内部有没有什么合规政策需要遵守？",
     "这个项目有没有一个硬性的上线时间或验收日期？",
     "所以我记下了（列举约束）——还有没有我没问到的限制条件？"),

    ("success_criteria", 0.03, "验收标准",
     "什么样的结果会让你觉得这个项目是成功的？有没有可量化的期望？",
     "比如：审批时间从 5 天缩短到 1 天？或者出错率降低 90%？",
     "所以主要验收标准是（列举）——这些标准可以用来在项目结束后检验效果。"),
]


# ── Scene-aware weight multipliers ──
# Key: scene name (matches SceneType values), Value: {field_name: multiplier}
# Default multiplier = 1.0 (unchanged)

_SCENE_WEIGHT_MULTIPLIERS: dict[str, dict[str, float]] = {
    "报表_BI看板": {
        "data_scale": 2.5,              # BI project — data volume is critical
        "functional_requirements": 1.5,  # report dimensions + metrics
        "user_roles": 1.3,               # who views which report
        "business_flow": 0.5,            # flow is less critical for BI
        "current_process": 0.5,
    },
    "审批流系统": {
        "business_flow": 2.0,            # approval flow is the core
        "user_roles": 1.5,               # approval matrix is critical
        "non_functional": 1.3,           # audit compliance
        "data_scale": 0.5,               # data volume less critical
    },
    "系统改造升级": {
        "existing_systems": 1.8,          # migration + integration are key
        "current_process": 1.5,           # what exists matters most
        "constraints": 1.5,              # risk + transition constraints
        "project_name": 1.2,
    },
    "数据治理项目": {
        "data_scale": 2.0,
        "existing_systems": 1.5,
        "non_functional": 1.5,            # data quality rules
        "user_roles": 0.5,
        "business_flow": 0.5,
    },
    "接口集成项目": {
        "existing_systems": 2.0,
        "non_functional": 1.5,            # reliability + error handling
        "business_flow": 0.5,
        "user_roles": 0.5,
    },
    "简单工具类": {
        "functional_requirements": 1.8,
        "user_roles": 1.3,
        "business_flow": 0.3,
        "existing_systems": 0.3,
        "non_functional": 0.3,
        "data_scale": 0.3,
        "constraints": 0.3,
    },
    # 新建系统 — no overrides, all 1.0
}


# ── Scene detection (lightweight, mirrors planner.py logic) ──

def _list_count(profile: dict, field: str) -> int:
    v = profile.get(field, [])
    return len(v) if isinstance(v, list) else 0


def _detect_scene(profile: dict) -> str:
    """Quick scene detection from profile fields. Matches planner.py logic."""
    import json as _json

    def _txt(*fields: str) -> str:
        parts = []
        for f in fields:
            v = profile.get(f, "")
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, (list, dict)):
                parts.append(_json.dumps(v, ensure_ascii=False))
        return " ".join(parts)

    text = _txt("business_background", "current_process", "business_flow")
    funcs_text = _txt("functional_requirements")
    role_count = _list_count(profile, "user_roles")
    func_count = _list_count(profile, "functional_requirements")

    if profile.get("existing_systems") and re.search(r"优化|升级|改造|替换|二期|迭代|重构|切换|迁移", text):
        return "系统改造升级"
    if re.search(r"报表|看[板幕]|统计|仪表盘|BI|大屏|驾驶舱|趋势图|数据分析", funcs_text):
        if not re.search(r"审批|审核|下单|采购|报销|入库|出库|生产", text):
            return "报表_BI看板"
    if re.search(r"审批|审核|复核|会签|签批|报销|审批流", text) and role_count >= 3:
        return "审批流系统"
    if profile.get("data_scale") and re.search(r"数据质量|数据标准|数据迁移|数据治理|数据清洗|数据规范|主数据", text):
        return "数据治理项目"
    if _list_count(profile, "existing_systems") >= 2 and func_count <= 3:
        if not re.search(r"界面|页面|录入|填写|填报", funcs_text):
            return "接口集成项目"
    if role_count <= 2 and func_count <= 3 and not profile.get("existing_systems"):
        if not profile.get("business_flow"):
            return "简单工具类"
    return "新建系统"


# ── Build scene-weighted rules ──

def _get_weighted_field_rules(scene: str) -> list[tuple]:
    """Return FIELD_RULES with weights adjusted for the given scene."""
    multipliers = _SCENE_WEIGHT_MULTIPLIERS.get(scene, {})
    rules = []
    for field, weight, label, q1, q2, q3 in _BASE_FIELD_RULES:
        mult = multipliers.get(field, 1.0)
        adjusted = round(weight * mult, 3)
        rules.append((field, adjusted, label, q1, q2, q3))
    return rules


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(value)


def evaluate_profile_completeness(thread_id: str = "default") -> CompletenessResult:
    """Evaluate the current profile completeness and generate probing questions.

    Weights are dynamically adjusted based on detected project scene.
    """
    thread_id = resolve_thread_id(thread_id)
    profile = get_profile(thread_id)

    scene = _detect_scene(profile)
    rules = _get_weighted_field_rules(scene)

    score = 0.0
    missing_fields: list[str] = []
    suggested_questions: list[str] = []

    for field, weight, label, q1, q2, q3 in rules:
        if _has_value(profile.get(field)):
            score += weight
        else:
            missing_fields.append(label)
            suggested_questions.append(q1)

    score = round(min(score, 1.0), 2)
    profile["sufficiency_score"] = score
    profile["pending_questions"] = suggested_questions[:3]

    covered_count = len(rules) - len(missing_fields)
    reasoning = f"已覆盖 {covered_count}/{len(rules)} 类需求信息（场景：{scene}）。"

    return CompletenessResult(
        score=score,
        missing_fields=missing_fields,
        suggested_questions=suggested_questions[:3],
        reasoning=reasoning,
    )


@tool
def evaluate_completeness(thread_id: str = "default") -> str:
    """Evaluate how complete the current requirement profile is.

    Returns a score (0.0-1.0), list of missing fields, and suggested
    next questions. Call this after each round of profile updates to
    decide whether to continue gathering or suggest generating the PRD.

    Args:
        thread_id: Session thread ID

    Returns:
        Structured evaluation result
    """
    result = evaluate_profile_completeness(thread_id)
    missing = "、".join(result.missing_fields) if result.missing_fields else "无"
    questions = result.suggested_questions or ["信息已经较完整，可以生成 PRD。"]
    return (
        f"**需求完整度: {result.score:.0%}**\n"
        f"**分析:** {result.reasoning}\n"
        f"**待完善:** {missing}\n"
        f"**建议追问:**\n- "
        + "\n- ".join(questions)
    )


# ── Backward-compatible aliases ──

SufficiencyResult = CompletenessResult
evaluate_sufficiency = evaluate_completeness
evaluate_profile_sufficiency = evaluate_profile_completeness
