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
        # Thought event 1: scene recognition
        scene_label = profile.get("_scene_label", "")
        if not scene_label:
            from app.agent.pm.phase2.planner import prd_planner
            scene_label = prd_planner.get_scene_label(profile)
        yield {
            "type": "thought",
            "data": {
                "phase": "planning",
                "text": (
                    f"已识别项目场景为「{scene_label}」"
                    f"，将根据场景特点调整章节重点"
                ),
            },
        }

        # Thought event 2: section strategy
        mode_label = "一次性生成" if mode == "one_shot" else "逐章生成"
        yield {
            "type": "thought",
            "data": {
                "phase": "planning",
                "text": (
                    f"本次 PRD 共 {len(sections)} 个章节"
                    f"，采用「{mode_label}」模式"
                ),
            },
        }

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
            # Thought event 3: per-section generation
            yield {
                "type": "thought",
                "data": {
                    "phase": "section_start",
                    "text": (
                        f"正在撰写「{section['title']}」"
                        f"（第 {i+1}/{len(sections)} 章）"
                    ),
                },
            }

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
