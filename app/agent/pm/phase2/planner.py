"""Phase 2: PRD section planner."""

from loguru import logger

from app.agent.pm.prompts import PRD_SECTION_ORDER, PRD_SECTION_TEMPLATES


class PRDPlanner:

    def __init__(self):
        self.sections = [
            {
                "key": key,
                "title": PRD_SECTION_TEMPLATES[key]["title"],
                "status": "pending",
            }
            for key in PRD_SECTION_ORDER
        ]

    def plan(self, profile: dict, mode: str = "one_shot") -> list[dict]:
        """Plan PRD sections based on the requirement profile.

        Args:
            profile: The completed RequirementProfile
            mode: "one_shot" or "incremental"

        Returns:
            List of section dicts with key, title, status, and prompt
        """
        sections = []
        for key in PRD_SECTION_ORDER:
            template = PRD_SECTION_TEMPLATES[key]
            prompt = template["prompt"].format(
                profile_context=self._format_profile(profile)
            )
            sections.append({
                "key": key,
                "title": template["title"],
                "status": "pending",
                "prompt": prompt,
                "content": "",
            })
        logger.info(f"PRD plan created: {len(sections)} sections, mode={mode}")
        return sections

    def _format_profile(self, profile: dict) -> str:
        import json
        return json.dumps(profile, ensure_ascii=False, indent=2)


prd_planner = PRDPlanner()
