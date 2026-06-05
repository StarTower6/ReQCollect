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
    ("project_name", 0.05, "项目名称", "这个需求一般怎么称呼？有项目名称了吗？"),
    ("business_background", 0.12, "业务背景与痛点",
     "目前这个业务是怎么跑的？遇到了什么问题？"),
    ("current_process", 0.12, "现状流程",
     "现在是手工做还是有系统在跑？具体流程是怎样的？"),
    ("user_roles", 0.15, "使用角色",
     "涉及哪些角色和部门？大概各有多少人用？"),
    ("business_flow", 0.10, "业务流程",
     "核心业务链路是怎样的？从发起到结束大致分几步？"),
    ("functional_requirements", 0.15, "功能需求",
     "需要系统支持哪些核心功能？"),
    ("existing_systems", 0.10, "系统对接",
     "要和公司现有的哪些系统打通？用友ERP/OA/MES/HR？"),
    ("non_functional", 0.08, "非功能需求",
     "性能、并发、安全、合规方面有没有要求？"),
    ("data_scale", 0.05, "数据量级",
     "大概有多少用户使用？每天处理多少数据？"),
    ("constraints", 0.05, "约束条件",
     "工期、预算、技术路线有没有限制？"),
    ("success_criteria", 0.03, "验收标准",
     "做出来怎么算做成？有没有量化的期望指标？"),
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
