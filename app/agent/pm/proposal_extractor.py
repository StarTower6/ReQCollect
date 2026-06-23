"""Extract requirement proposals from session conversations via LLM."""

from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.config import config
from app.core.llm_factory import llm_factory
from app.db import DataStore


EXTRACTION_SYSTEM_PROMPT = """\
You are a senior product analyst. Given a conversation history from a business user
describing their needs for a software system, extract a structured requirement proposal.

Output valid JSON with these fields (use empty string/list for missing info):

{
  "title": "Short summary (max 100 chars)",
  "background": "Business context - why is this needed?",
  "pain_points": ["List", "of", "core", "pain", "points"],
  "desired_outcome": "What success looks like / expected result",
  "scope_note": "What's in / out of scope, assumptions, constraints",
  "tags": ["relevant", "tags"]
}

Rules:
- title must be concise, actionable
- pain_points as a JSON array of strings
- Use the original language (Chinese or English) as the user
- Only include information actually mentioned in the conversation
- Do NOT fabricate details not discussed

Return ONLY the JSON object, no markdown fences, no explanation.
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

        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines).strip()

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
