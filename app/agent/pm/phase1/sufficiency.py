"""Information sufficiency evaluator for requirement profiles."""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.agent.pm.tools import get_profile, resolve_thread_id


class SufficiencyResult(BaseModel):
    score: float = Field(description="Sufficiency score 0.0 to 1.0")
    missing_fields: list[str] = Field(description="Fields that still need to be filled")
    suggested_questions: list[str] = Field(description="Suggested questions to ask the user next")
    reasoning: str = Field(description="Brief reasoning for the score")


FIELD_RULES = [
    ("project_name", 0.08, "项目名称", "这个产品/项目准备叫什么名字？"),
    ("project_type", 0.08, "项目类型", "这是内部系统、SaaS 产品、移动应用，还是其他类型？"),
    ("industry", 0.07, "行业领域", "这个需求主要服务哪个行业或业务场景？"),
    ("elevator_pitch", 0.12, "核心价值", "它最核心要解决的用户痛点是什么？"),
    ("user_roles", 0.15, "用户角色", "主要用户角色有哪些？"),
    ("functional_modules", 0.20, "功能模块", "需要覆盖哪些核心功能模块？"),
    ("non_functional", 0.10, "非功能需求", "性能、安全、可用性或合规方面有什么要求？"),
    ("constraints", 0.07, "约束条件", "有哪些技术、预算、周期或系统集成约束？"),
    ("assumptions", 0.05, "关键假设", "当前有哪些需要先默认成立的业务或技术假设？"),
    ("covered_topics", 0.08, "已覆盖议题", "还需要确认哪些需求议题已经讨论过？"),
]


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(value)


def evaluate_profile_sufficiency(thread_id: str = "default") -> SufficiencyResult:
    """Evaluate and persist the current profile sufficiency without external LLM calls."""
    thread_id = resolve_thread_id(thread_id)
    profile = get_profile(thread_id)

    score = 0.0
    missing_fields: list[str] = []
    suggested_questions: list[str] = []

    for field, weight, label, question in FIELD_RULES:
        if _has_value(profile.get(field)):
            score += weight
        else:
            missing_fields.append(label)
            suggested_questions.append(question)

    score = round(min(score, 1.0), 2)
    profile["sufficiency_score"] = score
    profile["pending_questions"] = suggested_questions[:3]

    covered_count = len(FIELD_RULES) - len(missing_fields)
    reasoning = f"已覆盖 {covered_count}/{len(FIELD_RULES)} 类需求信息。"

    return SufficiencyResult(
        score=score,
        missing_fields=missing_fields,
        suggested_questions=suggested_questions[:3],
        reasoning=reasoning,
    )


@tool
def evaluate_sufficiency(thread_id: str = "default") -> str:
    """Evaluate how complete the current requirement profile is.

    Returns a score (0.0-1.0), list of missing fields, and suggested
    next questions. Call this after each round of profile updates to
    decide whether to continue mining or suggest generating the PRD.

    Args:
        thread_id: Session thread ID

    Returns:
        Structured evaluation result
    """
    result = evaluate_profile_sufficiency(thread_id)
    missing = ", ".join(result.missing_fields) if result.missing_fields else "无"
    questions = result.suggested_questions or ["信息已经较完整，可以生成 PRD。"]
    return (
        f"**Sufficiency Score: {result.score:.0%}**\n"
        f"**Reasoning:** {result.reasoning}\n"
        f"**Missing:** {missing}\n"
        f"**Suggested next questions:**\n- "
        + "\n- ".join(questions)
    )
