"""PM-specific LangChain tools for requirement profile management."""

import json
from contextvars import ContextVar

from langchain_core.tools import tool
from loguru import logger

PROFILE_DEFAULTS = {
    "project_name": "",
    "project_type": "",
    "industry": "",
    "elevator_pitch": "",
    "user_roles": [],
    "functional_modules": [],
    "non_functional": {},
    "constraints": [],
    "assumptions": [],
    "covered_topics": [],
    "pending_questions": [],
    "sufficiency_score": 0.0,
}

_profile_store: dict[str, dict] = {}
_current_thread_id: ContextVar[str] = ContextVar("pm_current_thread_id", default="default")


def set_current_thread_id(thread_id: str):
    return _current_thread_id.set(thread_id)


def reset_current_thread_id(token) -> None:
    _current_thread_id.reset(token)


def resolve_thread_id(thread_id: str = "default") -> str:
    return _current_thread_id.get() if thread_id == "default" else thread_id


def get_profile_store() -> dict[str, dict]:
    return _profile_store


def get_profile(thread_id: str) -> dict:
    thread_id = resolve_thread_id(thread_id)
    if thread_id not in _profile_store:
        _profile_store[thread_id] = {
            key: value.copy() if isinstance(value, (list, dict)) else value
            for key, value in PROFILE_DEFAULTS.items()
        }
    return _profile_store[thread_id]


def _is_empty_profile_value(value) -> bool:
    return value is None or value == "" or value == [] or value == {} or value == 0.0


def hydrate_profile(thread_id: str, data: dict | None) -> dict:
    """Merge persisted profile data into the in-memory tool profile."""
    profile = get_profile(thread_id)
    if not data:
        return profile
    for key in PROFILE_DEFAULTS:
        if key in data and data[key] is not None:
            current = profile.get(key)
            incoming = data[key]
            if _is_empty_profile_value(current) or not _is_empty_profile_value(incoming):
                if key == "sufficiency_score":
                    profile[key] = max(float(current or 0.0), float(incoming or 0.0))
                elif not _is_empty_profile_value(incoming):
                    profile[key] = incoming
    return profile


@tool
def update_requirement_profile(
    field: str,
    value: str,
    thread_id: str = "default",
) -> str:
    """Update a field in the requirement profile.

    Use this to record every insight you extract from the conversation.
    Call it immediately after the user confirms or clarifies a requirement.

    Args:
        field: The profile field to update. One of:
            project_name, project_type, industry, elevator_pitch,
            user_roles (JSON array string), functional_modules (JSON array string),
            non_functional (JSON object string), constraints (JSON array string),
            assumptions (JSON array string), covered_topics (JSON array string),
            pending_questions (JSON array string)
        value: The value to set. For list/dict fields, pass a JSON string.
        thread_id: Session thread ID

    Returns:
        Confirmation of what was updated
    """
    thread_id = resolve_thread_id(thread_id)
    profile = get_profile(thread_id)
    list_fields = {"user_roles", "functional_modules", "constraints",
                   "assumptions", "covered_topics", "pending_questions"}
    dict_fields = {"non_functional"}

    if field in list_fields:
        try:
            profile[field] = json.loads(value)
        except json.JSONDecodeError:
            profile[field] = [value]
    elif field in dict_fields:
        try:
            profile[field] = json.loads(value)
        except json.JSONDecodeError:
            profile[field] = {"raw": value}
    else:
        profile[field] = value

    logger.info(f"[{thread_id}] Profile updated: {field}")
    return f"Requirement profile field '{field}' updated successfully."


@tool
def get_profile_summary(thread_id: str = "default") -> str:
    """Get a summary of the current requirement profile.

    Use this to check what you've already covered and what's still missing.
    Call it before deciding what to ask next.

    Args:
        thread_id: Session thread ID

    Returns:
        Summary of current profile state
    """
    thread_id = resolve_thread_id(thread_id)
    profile = get_profile(thread_id)
    filled = {k: v for k, v in profile.items()
              if v and v != [] and v != {} and v != 0.0 and k not in ("pending_questions", "covered_topics", "sufficiency_score")}
    empty = [k for k, v in profile.items()
             if (v == "" or v == [] or v == {} or v == 0.0) and k not in ("pending_questions", "covered_topics", "sufficiency_score")]

    lines = ["## Current Requirement Profile Summary", ""]
    lines.append(f"**Score:** {profile.get('sufficiency_score', 0.0):.0%}")
    lines.append("")
    if filled:
        lines.append("### Covered")
        for k, v in filled.items():
            val_str = json.dumps(v, ensure_ascii=False)
            if len(val_str) > 120:
                val_str = val_str[:120] + "..."
            lines.append(f"- **{k}**: {val_str}")
    if empty:
        lines.append("")
        lines.append("### Not Yet Covered")
        for k in empty:
            lines.append(f"- {k}")
    if profile.get("pending_questions"):
        lines.append("")
        lines.append("### Pending Questions")
        for q in profile["pending_questions"]:
            lines.append(f"- {q}")
    return "\n".join(lines)


@tool
def set_pending_questions(questions_json: str, thread_id: str = "default") -> str:
    """Set the list of questions you still need to ask the user.

    Args:
        questions_json: JSON array of question strings
        thread_id: Session thread ID

    Returns:
        Confirmation
    """
    thread_id = resolve_thread_id(thread_id)
    profile = get_profile(thread_id)
    try:
        profile["pending_questions"] = json.loads(questions_json)
    except json.JSONDecodeError:
        profile["pending_questions"] = [questions_json]
    return f"Pending questions updated: {len(profile['pending_questions'])} questions."
