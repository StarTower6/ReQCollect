"""PM agent service — conversational requirement mining and PRD generation.

Now backed by DataStore (MySQL or JSON file fallback) instead of in-memory dicts.
"""

import json
import os
from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger

from app.agent.pm.phase1.mining_agent import get_mining_agent
from app.agent.pm.phase1.profile_extractor import apply_profile_hints
from app.agent.pm.phase1.sufficiency import evaluate_profile_sufficiency
from app.agent.pm.phase2.assembler import prd_assembler
from app.agent.pm.phase2.planner import prd_planner
from app.agent.pm.tools import get_profile, hydrate_profile, set_datastore_for_tools
from app.db import DataStore
from app.config import config

_session_state: dict[str, dict] = {}  # kept for incremental generation state
# Module-level sentinel — swapped by main.py lifespan with real instance
pm_agent_service: "PMAgentService | None" = None


def _detect_intent(message: str) -> str:
    """Returns 'generate' | 'continue' | 'chat'."""
    gen_kw = ["生成prd", "生成文档", "生成需求", "写prd", "写文档",
              "出文档", "开始写", "开始生成", "出需求文档", "输出prd", "输出文档"]
    cont_kw = ["继续", "下一章", "next", "继续生成", "下一步"]

    msg = message.strip().lower()
    for kw in cont_kw:
        if kw in msg:
            return "continue"
    for kw in gen_kw:
        if kw in msg:
            return "generate"
    return "chat"


class PMAgentService:
    """PM Agent service with DataStore persistence."""

    def __init__(self, datastore: DataStore):
        self._ds = datastore
        # Wire the DataStore into tools for profile access
        set_datastore_for_tools(datastore)

    # ── Phase 1: Chat / Requirement Mining ──

    async def chat(
        self,
        message: str,
        thread_id: str = "default",
        use_knowledge: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 1: Conversational requirement mining."""
        logger.info(f"[{thread_id}] Chat: {message[:100]}..., use_knowledge={use_knowledge}")

        # Ensure session exists
        session = await self._ds.get_session(thread_id)
        if session is None:
            session = await self._ds.create_session(thread_id)

        # Apply profile extraction hints from the user message
        hinted_fields = apply_profile_hints(thread_id, message)
        if hinted_fields:
            logger.info(f"[{thread_id}] Profile hints extracted: {', '.join(hinted_fields)}")
            evaluate_profile_sufficiency(thread_id)

        # Save user message
        await self._ds.save_message(thread_id, "user", message)

        assistant_content = ""
        async for event in get_mining_agent().chat(
            message,
            thread_id,
            force_knowledge=use_knowledge,
        ):
            if event.get("type") == "content" and isinstance(event.get("data"), str):
                assistant_content += event["data"]
            yield event

        if assistant_content.strip():
            await self._ds.save_message(thread_id, "assistant", assistant_content)

        # Persist profile via DataStore
        profile = get_profile(thread_id)
        await self._ds.save_profile(thread_id, profile)

    # ── Phase 2: PRD Generation ──

    async def generate_prd(
        self, thread_id: str = "default", mode: str = "one_shot",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 2: Full PRD generation from current profile."""
        logger.info(f"[{thread_id}] Generate PRD, mode={mode}")
        session = _get_session(thread_id)
        session["mode"] = mode

        profile = get_profile(thread_id)
        sections = prd_planner.plan(profile, mode)
        session["prd_sections"] = sections
        session["current_section_index"] = 0

        async for event in prd_assembler.assemble(sections, profile, mode):
            if event.get("type") == "prd_complete":
                markdown = event["data"]["markdown"]
                prd_data = {
                    "project_name": profile.get("project_name", "PRD"),
                    "mode": mode,
                    "sections": [{"key": s["key"], "title": s["title"], "status": s.get("status", "done")} for s in sections],
                    "markdown": markdown,
                }
                # Save via DataStore
                project_name = profile.get("project_name", "PRD")
                await self._ds.save_prd(
                    thread_id,
                    project_name=project_name,
                    mode=mode,
                    sections=prd_data["sections"],
                    markdown=markdown,
                )
                await self._ds.save_message(
                    thread_id, "assistant", markdown,
                    event_type="prd_complete", meta={"mode": mode},
                )
            yield event

    async def continue_generation(
        self, thread_id: str = "default",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 2: Continue incremental generation from last completed section."""
        session = _get_session(thread_id)
        sections = session.get("prd_sections")
        if sections is None:
            async for event in self.generate_prd(thread_id, "incremental"):
                yield event
            return

        idx = session.get("current_section_index", 0)
        if idx >= len(sections):
            yield {"type": "status", "data": {"message": "All sections complete."}}
            return

        yield {"type": "status", "data": {"message": f"Continuing section {idx+1}/{len(sections)}..."}}

        for i in range(idx, len(sections)):
            section = sections[i]
            yield {"type": "section_start", "data": {
                "section_key": section["key"], "title": section["title"],
                "index": i+1, "total": len(sections),
            }}

            from app.agent.pm.phase2.generator import get_section_generator
            content = ""
            async for chunk in get_section_generator().generate(section):
                content += chunk
                yield {"type": "section_content", "data": chunk}

            section["content"] = content
            section["status"] = "done"
            session["current_section_index"] = i + 1

            yield {"type": "section_complete", "data": {
                "section_key": section["key"], "title": section["title"],
                "content": content, "index": i+1, "total": len(sections),
            }}

            if i < len(sections) - 1:
                yield {"type": "awaiting_approval", "data": {
                    "message": f"'{section['title']}' done. POST /api/pm/continue to proceed.",
                    "next_section": sections[i+1]["title"], "next_index": i + 1,
                }}
                return

        profile = get_profile(thread_id)
        title = f"# {profile.get('project_name', 'PRD')}\n\n"
        title += f"> {profile.get('elevator_pitch', '')}\n\n---\n\n"
        full_md = title + "\n\n".join(s["content"] for s in sections if s.get("content"))

        await self._ds.save_prd(
            thread_id,
            project_name=profile.get("project_name", "PRD"),
            mode=session["mode"],
            sections=[{"key": s["key"], "title": s["title"], "status": s.get("status", "done")} for s in sections],
            markdown=full_md,
        )
        await self._ds.save_message(
            thread_id, "assistant", full_md,
            event_type="prd_complete", meta={"mode": session["mode"]},
        )

        yield {"type": "prd_complete", "data": {
            "markdown": full_md,
            "sections": [{"key": s["key"], "title": s["title"], "status": s.get("status", "done")} for s in sections],
        }}

    # ── Convenience wrapper ──

    async def handle(
        self,
        message: str,
        thread_id: str = "default",
        mode: str = "one_shot",
        use_knowledge: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Convenience wrapper: auto-routes based on message intent."""
        intent = _detect_intent(message)
        logger.info(f"[{thread_id}] handle, intent={intent}, use_knowledge={use_knowledge}")

        if intent == "generate":
            await self._ds.save_message(thread_id, "user", message, event_type="command")
            async for event in self.generate_prd(thread_id, mode):
                yield event
        elif intent == "continue":
            await self._ds.save_message(thread_id, "user", message, event_type="command")
            async for event in self.continue_generation(thread_id):
                yield event
        else:
            async for event in self.chat(message, thread_id, use_knowledge=use_knowledge):
                yield event

    # ── Data accessors ──

    async def get_profile(self, thread_id: str = "default") -> dict:
        return await self._ds.get_profile(thread_id)

    async def get_prd(self, thread_id: str = "default") -> dict | None:
        return await self._ds.get_prd(thread_id)

    async def get_message_history(self, thread_id: str = "default") -> list[dict]:
        return await self._ds.get_message_history(thread_id)

    async def list_sessions(self) -> list[dict]:
        return await self._ds.list_sessions()

    async def delete_session(self, session_id: str) -> bool:
        _session_state.pop(session_id, None)
        return await self._ds.delete_session(session_id)

    async def cleanup(self):
        await get_mining_agent().close()

    # ── Dashboard / Stats (P1) ──

    async def get_dashboard_overview(self) -> dict:
        return await self._ds.get_dashboard_overview()

    async def get_trend_data(self, granularity: str = "day", days: int = 30) -> list[dict]:
        return await self._ds.get_trend_data(granularity, days)

    # ── Export (P1) ──

    async def export_sessions(self) -> list[dict]:
        """Return all sessions for export (no pagination)."""
        return await self._ds.list_sessions(limit=10000)

    async def export_prds(self) -> list[dict]:
        """Return all PRDs across sessions for export."""
        sessions = await self._ds.list_sessions(limit=10000)
        results = []
        for s in sessions:
            prd = await self._ds.get_prd(s["session_id"])
            if prd:
                results.append({
                    "session_id": s["session_id"],
                    "project_name": s.get("project_name", ""),
                    "version": prd.get("version", 1),
                    "mode": prd.get("mode", ""),
                    "created_at": prd.get("created_at", ""),
                    "markdown_preview": prd.get("markdown", "")[:200],
                })
        return results

    async def log_audit(self, action: str, user_id: str = "", session_id: str = "",
                        detail: dict | None = None, ip_address: str = "") -> None:
        await self._ds.log_audit(action, user_id, session_id, detail, ip_address)


def _get_session(thread_id: str) -> dict:
    if thread_id not in _session_state:
        _session_state[thread_id] = {
            "mode": "one_shot",
            "prd_sections": None,
            "current_section_index": 0,
        }
    return _session_state[thread_id]
