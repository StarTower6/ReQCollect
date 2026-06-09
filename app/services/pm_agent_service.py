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
from app.agent.pm.prompts_import import IMPORT_ANALYSIS_PROMPT
from app.core.file_handler import decode_content, save_import_file, validate_upload
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
        user_id: str | None = None,
        use_knowledge: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 1: Conversational requirement mining."""
        logger.info(f"[{thread_id}] Chat: {message[:100]}..., use_knowledge={use_knowledge}")

        # Ensure session exists
        session = await self._ds.get_session(thread_id)
        if session is None:
            session = await self._ds.create_session(thread_id, user_id=user_id or "default")

        # Load profile from DataStore into in-memory store for this thread
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

    # ── Import / Document Analysis ──

    async def import_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Import a .md document — create session + AI analysis + yield SSE events.

        Flow:
          1. Validate and save file
          2. Create new session in DataStore
          3. Record import in DataStore
          4. Inject document content as context message
          5. Run import analysis with custom system prompt
          6. Extract profile fields with source tags
          7. Yield import_complete event with session_id
        """
        logger.info(f"Import document: {filename}")

        # 1. Validate
        validate_upload(filename, file_content)
        text_content = decode_content(file_content)

        # 2. Create new session
        import uuid
        session_id = "import-" + uuid.uuid4().hex[:12]
        await self._ds.create_session(session_id, user_id=user_id, project_name=f"导入分析：{filename}")

        # 3. Save file
        file_path = save_import_file(session_id, filename, file_content)

        # 4. Record import
        await self._ds.save_import_record(session_id, filename, file_path)

        # 5. Save user message (the file content as a "user" message)
        await self._ds.save_message(
            session_id, "user",
            f"[导入文档: {filename}]\n\n{text_content[:500]}...",
            event_type="import",
            meta={"filename": filename, "file_path": file_path, "truncated": len(text_content) > 500},
        )

        yield {"type": "import_analysis", "data": {"session_id": session_id, "filename": filename}}

        # 6. Build context: document full text as a system-level message
        context_messages = [
            {
                "role": "system",
                "content": f"以下是一份用户上传的需求相关文档，请仔细阅读并从中提取需求画像字段。\n\n文档名称：{filename}\n\n---\n\n{text_content}",
            },
        ]

        # 7. Run analysis with import-specific prompt
        assistant_content = ""
        async for event in get_mining_agent().chat_with_context(
            message=f"请分析上传的文档「{filename}」并提取需求信息，标记来源，然后总结已获取和缺失的字段。",
            thread_id=session_id,
            system_prompt_override=IMPORT_ANALYSIS_PROMPT,
            context_messages=context_messages,
        ):
            if event.get("type") == "content" and isinstance(event.get("data"), str):
                assistant_content += event["data"]
            yield event

        # 8. Save assistant response
        if assistant_content.strip():
            await self._ds.save_message(session_id, "assistant", assistant_content)

        # 9. Persist profile
        profile = get_profile(session_id)
        await self._ds.save_profile(session_id, profile)

        # 10. Yield import_complete
        yield {
            "type": "import_complete",
            "data": {
                "session_id": session_id,
                "filename": filename,
                "fields_filled": [k for k, v in profile.items() if v and k != "sufficiency_score"],
            },
        }

    async def upload_to_session(
        self,
        session_id: str,
        file_content: bytes,
        filename: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Upload a .md file to an existing session as conversation context.

        The document content is injected into the next LLM turn as context.
        """
        logger.info(f"Upload to session {session_id}: {filename}")

        # 1. Validate
        validate_upload(filename, file_content)
        text_content = decode_content(file_content)

        # 2. Save file
        file_path = save_import_file(session_id, filename, file_content)

        # 3. Record import
        await self._ds.save_import_record(session_id, filename, file_path)

        # 4. Save event message
        await self._ds.save_message(
            session_id, "user",
            f"[上传文档: {filename}]",
            event_type="file_upload",
            meta={"filename": filename, "file_path": file_path},
        )

        yield {"type": "import_analysis", "data": {"session_id": session_id, "filename": filename, "mode": "append"}}

        # 5. Inject document content as context for the AI to reference
        context_messages = [
            {
                "role": "system",
                "content": f"用户上传了一份文档供你参考. 请阅读下面的文档内容, 结合已有对话背景继续需求分析。\n\n文档名称：{filename}\n\n---\n\n{text_content}",
            },
        ]

        # 6. Use import prompt for the analysis step
        assistant_content = ""
        async for event in get_mining_agent().chat_with_context(
            message=f"我已上传文档「{filename}」。请参考文档内容，结合已有讨论继续需求分析。",
            thread_id=session_id,
            system_prompt_override=IMPORT_ANALYSIS_PROMPT,
            context_messages=context_messages,
        ):
            if event.get("type") == "content" and isinstance(event.get("data"), str):
                assistant_content += event["data"]
            yield event

        if assistant_content.strip():
            await self._ds.save_message(session_id, "assistant", assistant_content)

        # 7. Persist profile
        profile = get_profile(session_id)
        await self._ds.save_profile(session_id, profile)

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
        user_id: str | None = None,
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
            async for event in self.chat(message, thread_id, user_id=user_id, use_knowledge=use_knowledge):
                yield event

    # ── Data accessors ──

    async def get_session(self, session_id: str) -> dict | None:
        return await self._ds.get_session(session_id)

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
