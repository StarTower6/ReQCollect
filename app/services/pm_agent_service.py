"""PM agent service — individual endpoints for each phase + unified wrapper.

Core endpoints:
  - chat(message, thread_id)        → Phase 1 mining
  - generate_prd(thread_id, mode)   → Phase 2 full generation
  - continue_generation(thread_id)  → Phase 2 incremental next section

Convenience wrapper:
  - handle(message, thread_id, mode) → auto-routes based on intent
"""

from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger

from app.agent.pm.phase1.mining_agent import get_mining_agent
from app.agent.pm.phase1.profile_extractor import apply_profile_hints
from app.agent.pm.phase1.sufficiency import evaluate_profile_sufficiency
from app.agent.pm.phase2.assembler import prd_assembler
from app.agent.pm.phase2.planner import prd_planner
from app.agent.pm.tools import get_profile, hydrate_profile, remove_profile

_session_state: dict[str, dict] = {}


def _get_session(thread_id: str) -> dict:
    if thread_id not in _session_state:
        _session_state[thread_id] = {
            "mode": "one_shot",
            "prd_sections": None,
            "current_section_index": 0,
        }
    return _session_state[thread_id]


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

    # ── Core endpoints (individually callable) ──

    async def chat(
        self,
        message: str,
        thread_id: str = "default",
        use_knowledge: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 1: Conversational requirement mining."""
        logger.info(f"[{thread_id}] Chat: {message[:100]}..., use_knowledge={use_knowledge}")
        await self._load_profile(thread_id)
        hinted_fields = apply_profile_hints(thread_id, message)
        if hinted_fields:
            logger.info(f"[{thread_id}] Profile hints extracted: {', '.join(hinted_fields)}")
            evaluate_profile_sufficiency(thread_id)
            await self._save_profile(thread_id)
        await self._save_message(thread_id, "user", message)
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
            await self._save_message(thread_id, "assistant", assistant_content)
        # Persist profile to MySQL for session history
        await self._save_profile(thread_id)

    async def generate_prd(
        self, thread_id: str = "default", mode: str = "one_shot",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 2: Full PRD generation from current profile."""
        logger.info(f"[{thread_id}] Generate PRD, mode={mode}")
        await self._load_profile(thread_id)
        session = _get_session(thread_id)
        session["mode"] = mode

        profile = get_profile(thread_id)
        sections = prd_planner.plan(profile, mode)
        session["prd_sections"] = sections
        session["current_section_index"] = 0

        async for event in prd_assembler.assemble(sections, profile, mode):
            if event.get("type") == "prd_complete":
                await self._save_prd(thread_id, profile, mode, sections, event["data"]["markdown"])
                await self._save_message(
                    thread_id,
                    "assistant",
                    event["data"]["markdown"],
                    event_type="prd_complete",
                    meta={"mode": mode},
                )
            yield event

    async def continue_generation(
        self, thread_id: str = "default",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 2: Continue incremental generation from last completed section."""
        await self._load_profile(thread_id)
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

        await self._save_prd(thread_id, profile, session["mode"], sections, full_md)
        await self._save_message(
            thread_id,
            "assistant",
            full_md,
            event_type="prd_complete",
            meta={"mode": session["mode"]},
        )
        yield {"type": "prd_complete", "data": {
            "markdown": full_md,
            "sections": [{"key": s["key"], "title": s["title"], "status": s.get("status","done")} for s in sections],
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
            await self._save_message(thread_id, "user", message, event_type="command")
            async for event in self.generate_prd(thread_id, mode):
                yield event
        elif intent == "continue":
            await self._save_message(thread_id, "user", message, event_type="command")
            async for event in self.continue_generation(thread_id):
                yield event
        else:
            async for event in self.chat(message, thread_id, use_knowledge=use_knowledge):
                yield event

    # ── Helpers ──

    async def _load_profile(self, thread_id: str) -> dict:
        try:
            from app.db.database import AsyncSessionLocal
            from app.db.repository import ProfileRepository
            async with AsyncSessionLocal() as db_session:
                persisted = await ProfileRepository.get_by_session(db_session, thread_id)
            return hydrate_profile(thread_id, persisted)
        except Exception as e:
            logger.warning(f"[{thread_id}] Failed to load persisted profile: {e}")
            return get_profile(thread_id)

    async def _save_profile(self, thread_id: str) -> None:
        try:
            from app.db.database import AsyncSessionLocal
            from app.db.repository import ProfileRepository
            profile = get_profile(thread_id)
            async with AsyncSessionLocal() as db_session:
                await ProfileRepository.update_from_dict(db_session, thread_id, profile)
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")

    async def _save_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        event_type: str = "message",
        meta: dict | None = None,
    ) -> None:
        if not content.strip():
            return
        try:
            from app.db.database import AsyncSessionLocal
            from app.db.repository import ChatHistoryRepository
            async with AsyncSessionLocal() as db_session:
                await ChatHistoryRepository.add_message(
                    db_session,
                    session_id=thread_id,
                    role=role,
                    content=content,
                    event_type=event_type,
                    meta=meta,
                )
        except Exception as e:
            logger.warning(f"[{thread_id}] Failed to save chat message: {e}")

    async def _save_prd(self, thread_id: str, profile: dict, mode: str,
                        sections: list, markdown: str) -> None:
        try:
            from app.db.database import AsyncSessionLocal
            from app.db.repository import PRDRepository
            async with AsyncSessionLocal() as db_session:
                await PRDRepository.save(
                    db_session,
                    session_id=thread_id,
                    title=profile.get("project_name", "PRD"),
                    mode=mode,
                    sections=[{"key": s["key"], "title": s["title"], "status": s["status"]}
                              for s in sections],
                    markdown=markdown,
                )
            logger.info(f"[{thread_id}] PRD saved to MySQL")
        except Exception as e:
            logger.warning(f"[{thread_id}] Failed to save PRD to MySQL: {e}")

    async def get_profile(self, thread_id: str = "default") -> dict:
        return await self._load_profile(thread_id)

    async def forget_session(self, thread_id: str) -> None:
        _session_state.pop(thread_id, None)
        remove_profile(thread_id)

    async def cleanup(self):
        await get_mining_agent().close()


pm_agent_service = PMAgentService()
