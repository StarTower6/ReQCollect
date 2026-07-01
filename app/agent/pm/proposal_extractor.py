"""Extract requirement proposals from session conversations via LLM."""

from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.config import config
from app.core.llm_factory import llm_factory
from app.db import DataStore


EXTRACTION_SYSTEM_PROMPT = """\
You are a senior business analyst specialized in extracting requirement proposals from
customer conversations.

Given a conversation history between a business user and an AI consultant, extract a
structured proposal. Use common sense — if a pain point is clearly implied by the
conversation, list it. Be informative, not minimal.

Output ONLY a JSON object with these fields:

{
  "title": "Concise description of the business need — describe what the user wants, not the platform. e.g. '企业报销审批流程优化'",
  "background": "Synthesize the business context from the conversation — what situation prompted this need?",
  "pain_points": ["List specific pain points mentioned or clearly implied"],
  "desired_outcome": "What the user wants to achieve — the ideal end state",
  "scope_note": "Brief note on what's in scope and any assumptions",
  "tags": ["3-5", "relevant", "keywords"]
}

IMPORTANT:
- Every pain point must be a separate string in the array
- If pain points are implied from context clues, include them
- title should describe the BUSINESS NEED itself — what the user actually wants
- Do NOT include meta phrases like "基于多轮对话", "基于AI", "需求采集系统" in the title
- A good title example: "企业报销审批流程优化" not "基于多轮对话的报销系统"
- Use the original language of the conversation (Chinese inputs → Chinese outputs)
- Return ONLY the JSON object. No markdown, no explanation.
"""

FIELD_DISPLAY_NAMES = {
    "title": "提案标题",
    "background": "业务背景",
    "pain_points": "核心痛点",
    "desired_outcome": "期望效果",
    "scope_note": "范围说明",
    "tags": "标签",
}


async def extract_proposal_from_session(
    session_id: str,
    ds: DataStore,
) -> AsyncGenerator[dict, None]:
    """Extract a requirement proposal from a session's conversation history.

    Reads full chat history from the session, calls LLM to extract structured
    fields, then yields SSE events per field and a final proposal_done event.

    Args:
        session_id: The session to analyze
        ds: DataStore for reading message history

    Yields:
        dict events: {type: "proposal_field", field: str, content: ...}
        dict events: {type: "proposal_done", data: {...}}
    """
    import json as _json

    logger.info(f"[proposal_extract] session={session_id}")

    # 1. Load conversation messages
    messages = await ds.get_message_history(session_id)
    if not messages:
        logger.warning(f"[proposal_extract] No messages in session {session_id}")
        yield {
            "type": "proposal_done",
            "data": {
                "title": "",
                "background": "",
                "pain_points": [],
                "desired_outcome": "",
                "scope_note": "",
                "tags": [],
            },
        }
        return

    # Build conversation transcript
    transcript_lines = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "user":
            transcript_lines.append(f"用户: {content}")
        elif role == "assistant":
            transcript_lines.append(f"AI: {content}")
        else:
            transcript_lines.append(f"{role}: {content}")

    conversation_text = "\n".join(transcript_lines[-100:])  # limit context window

    # 2. Call LLM
    llm = llm_factory.create_chat_model(
        model=config.llm_model,
        temperature=0.3,
        streaming=False,
    )

    llm_messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(
            content="请从以下对话中提取需求提案信息:\n\n" + conversation_text
        ),
    ]

    try:
        response = await llm.ainvoke(llm_messages)
        raw = response.content.strip()

        # Strip markdown fences robustly
        import re as _markdown_re
        raw = _markdown_re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = _markdown_re.sub(r'\n?\s*```$', '', raw)
        raw = raw.strip()

        result = _json.loads(raw)
        logger.info(f"[proposal_extract] extracted: {result.get('title', 'N/A')[:60]}")

    except Exception as e:
        logger.error(f"[proposal_extract] LLM parse failed: {e}")
        yield {
            "type": "proposal_done",
            "data": {
                "title": "",
                "background": "",
                "pain_points": [],
                "desired_outcome": "",
                "scope_note": "",
                "tags": [],
            },
        }
        return

    # 3. Yield fields one by one (SSE style), then final event
    ordered_fields = [
        "title", "background", "pain_points", "desired_outcome", "scope_note", "tags"
    ]

    for field in ordered_fields:
        value = result.get(field)
        if field in ("pain_points", "tags"):
            value = value if isinstance(value, list) else []
        elif isinstance(value, str) and value:
            pass
        else:
            value = ""

        yield {
            "type": "proposal_field",
            "field": field,
            "display_name": FIELD_DISPLAY_NAMES.get(field, field),
            "content": value,
        }

    # Final event with complete data
    data = {
        "title": result.get("title", ""),
        "background": result.get("background", ""),
        "pain_points": result.get("pain_points", []) if isinstance(result.get("pain_points"), list) else [],
        "desired_outcome": result.get("desired_outcome", ""),
        "scope_note": result.get("scope_note", ""),
        "tags": result.get("tags", []) if isinstance(result.get("tags"), list) else [],
    }

    yield {
        "type": "proposal_done",
        "data": data,
    }
