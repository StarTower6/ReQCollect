"""PM Agent state definitions."""

import operator
from typing import Annotated, TypedDict


class RequirementProfile(TypedDict, total=False):
    """Structured requirement profile — the bridge between Phase 1 and Phase 2."""

    project_name: str
    project_type: str
    industry: str
    elevator_pitch: str

    user_roles: list  # [{"role": "admin", "desc": "...", "concerns": [...]}]
    functional_modules: list  # [{"module": "auth", "features": [...], "priority": "P0"}]
    non_functional: dict  # {"performance": "...", "security": "...", ...}

    constraints: list[str]
    assumptions: list[str]

    covered_topics: list[str]
    pending_questions: list[str]
    sufficiency_score: float


class PMState(TypedDict):
    """Full PM Agent session state persisted in Redis checkpoint."""

    messages: Annotated[list, operator.add]
    profile: RequirementProfile
    phase: str  # "mining" | "generating" | "complete"
    generation_mode: str  # "one_shot" | "incremental"
    prd_sections: list  # [{"title": "...", "content": "...", "status": "pending|done"}]
    prd_markdown: str
