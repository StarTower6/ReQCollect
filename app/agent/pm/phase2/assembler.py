"""Phase 2: PRD document assembler with incremental control."""

from collections.abc import AsyncGenerator
from typing import Any

from app.agent.pm.phase2.generator import get_section_generator


class PRDAssembler:

    async def assemble(
        self,
        sections: list[dict],
        profile: dict,
        mode: str = "one_shot",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Assemble the full PRD by generating each section.

        Args:
            sections: List of section dicts from planner
            profile: Requirement profile
            mode: "one_shot" or "incremental"

        Yields:
            SSE events: prd_plan, section_start, section_content,
            section_complete, awaiting_approval, prd_complete
        """
        # Emit the plan
        plan_summary = [{"key": s["key"], "title": s["title"]} for s in sections]
        yield {
            "type": "prd_plan",
            "data": {
                "sections": plan_summary,
                "mode": mode,
            }
        }

        # Generate title
        title = f"# {profile.get('project_name', 'Product Requirements Document')}\n\n"
        title += f"> {profile.get('elevator_pitch', '')}\n\n"
        title += "---\n\n"
        full_markdown = title

        for i, section in enumerate(sections):
            yield {
                "type": "section_start",
                "data": {
                    "section_key": section["key"],
                    "title": section["title"],
                    "index": i + 1,
                    "total": len(sections),
                }
            }

            section_content = ""
            async for chunk in get_section_generator().generate(section):
                section_content += chunk
                yield {"type": "section_content", "data": chunk}

            section["content"] = section_content
            section["status"] = "done"
            full_markdown += section_content + "\n\n"

            yield {
                "type": "section_complete",
                "data": {
                    "section_key": section["key"],
                    "title": section["title"],
                    "content": section_content,
                    "index": i + 1,
                    "total": len(sections),
                }
            }

            if mode == "incremental" and i < len(sections) - 1:
                yield {
                    "type": "awaiting_approval",
                    "data": {
                        "message": f"Section '{section['title']}' complete. Continue to '{sections[i+1]['title']}'?",
                        "next_section": sections[i+1]["title"],
                    }
                }

        yield {
            "type": "prd_complete",
            "data": {
                "markdown": full_markdown,
                "sections": [{"key": s["key"], "title": s["title"], "status": s["status"]}
                           for s in sections],
            }
        }


prd_assembler = PRDAssembler()
