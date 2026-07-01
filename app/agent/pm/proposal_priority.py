"""Assess requirement proposal priority via LLM."""

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.config import config
from app.core.llm_factory import llm_factory


PRIORITY_SYSTEM_PROMPT = """\
You are a senior product manager. Assess the priority of a requirement proposal.

Evaluate these dimensions:
1. Impact scope: How many users/departments are affected?
2. Urgency: Is there business loss or compliance risk if delayed?
3. Dependencies: Does it require other systems to be ready first?
4. Implementation difficulty estimate

Priority levels:
- P0: Critical / blocking — must do immediately, affects core business
- P1: High — important, schedule this sprint/month
- P2: Medium — valuable, can schedule in next 2-3 months
- P3: Low — nice to have, no urgency

Return a JSON object:
{
  "priority": "P0|P1|P2|P3",
  "reasoning": "Brief justification in Chinese (max 200 chars)"
}

Return ONLY the JSON object, no markdown fences.
"""


async def assess_priority(proposal: dict) -> tuple[str, str]:
    """Assess proposal priority and return (priority, reasoning).

    Args:
        proposal: Dict with title, background, pain_points, desired_outcome, scope_note

    Returns:
        Tuple of (priority: str, reasoning: str)
    """
    import json as _json

    title = proposal.get("title", "")
    background = proposal.get("background", "")
    pain_points = proposal.get("pain_points", [])
    desired_outcome = proposal.get("desired_outcome", "")
    scope_note = proposal.get("scope_note", "")

    # Build a summary for the LLM
    if isinstance(pain_points, list):
        pain_text = "\n".join(f"  - {p}" for p in pain_points)
    else:
        pain_text = ""

    user_message = (
        "请评估以下需求提案的优先级:\n\n"
        f"标题: {title}\n\n"
        f"业务背景:\n{background}\n\n"
        f"核心痛点:\n{pain_text}\n\n"
        f"期望效果:\n{desired_outcome}\n\n"
        f"范围说明:\n{scope_note}\n\n"
        "请返回 JSON 格式的优先级评估结果。"
    )

    try:
        llm = llm_factory.create_chat_model(
            model=config.llm_model,
            temperature=0.2,
            streaming=False,
        )

        response = await llm.ainvoke([
            SystemMessage(content=PRIORITY_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])

        raw = response.content.strip()

        # Strip markdown fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines).strip()

        result = _json.loads(raw)
        priority = result.get("priority", "P2")
        reasoning = result.get("reasoning", "")

        # Validate priority value
        if priority not in ("P0", "P1", "P2", "P3"):
            priority = "P2"

        logger.info(f"[priority] assessed: {priority} — {reasoning[:80]}")

        return priority, reasoning

    except Exception as e:
        logger.warning(f"[priority] LLM assessment failed: {e}, defaulting to P2")
        pain_count = len(pain_points) if isinstance(pain_points, list) else 0
        has_outcome = bool(desired_outcome)
        fallback_reason = (
            f"自动评估 — "
            f"需求维度不完整"
            f"(痛点:{pain_count} 期望:{has_outcome})"
        )
        return "P2", fallback_reason
