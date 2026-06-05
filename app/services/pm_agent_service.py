"""PM agent service — conversational requirement mining and PRD generation (Lite: no DB)."""

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
from app.agent.pm.tools import get_profile, hydrate_profile, remove_profile
from app.config import config

_session_state: dict[str, dict] = {}
_message_history: dict[str, list[dict]] = {}
_prd_store: dict[str, dict] = {}


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


def _save_to_file(data: dict, filename: str):
    """Save data to JSON file for persistence across restarts."""
    try:
        filepath = os.path.join(config.data_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save {filename}: {e}")


def _load_from_file(filename: str) -> dict | None:
    """Load data from JSON file."""
    try:
        filepath = os.path.join(config.data_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {filename}: {e}")
    return None


class PMAgentService:

    async def chat(
        self,
        message: str,
        thread_id: str = "default",
        use_knowledge: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 1: Conversational requirement mining."""
        logger.info(f"[{thread_id}] Chat: {message[:100]}..., use_knowledge={use_knowledge}")

        # Apply profile extraction hints from the user message
        hinted_fields = apply_profile_hints(thread_id, message)
        if hinted_fields:
            logger.info(f"[{thread_id}] Profile hints extracted: {', '.join(hinted_fields)}")
            evaluate_profile_sufficiency(thread_id)

        # Save user message to in-memory history
        _save_message(thread_id, "user", message)

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
            _save_message(thread_id, "assistant", assistant_content)

        # Save profile to file for persistence
        profile = get_profile(thread_id)
        _save_to_file(profile, f"profile_{thread_id}.json")

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
                # Save PRD to in-memory store + file
                prd_data = {
                    "project_name": profile.get("project_name", "PRD"),
                    "mode": mode,
                    "sections": [{"key": s["key"], "title": s["title"], "status": s.get("status", "done")} for s in sections],
                    "markdown": markdown,
                }
                _prd_store[thread_id] = prd_data
                _save_to_file(prd_data, f"prd_{thread_id}.json")
                _save_message(thread_id, "assistant", markdown, event_type="prd_complete", meta={"mode": mode})
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

        prd_data = {
            "project_name": profile.get("project_name", "PRD"),
            "mode": session["mode"],
            "sections": [{"key": s["key"], "title": s["title"], "status": s.get("status", "done")} for s in sections],
            "markdown": full_md,
        }
        _prd_store[thread_id] = prd_data
        _save_to_file(prd_data, f"prd_{thread_id}.json")
        _save_message(thread_id, "assistant", full_md, event_type="prd_complete", meta={"mode": session["mode"]})

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
            _save_message(thread_id, "user", message, event_type="command")
            async for event in self.generate_prd(thread_id, mode):
                yield event
        elif intent == "continue":
            _save_message(thread_id, "user", message, event_type="command")
            async for event in self.continue_generation(thread_id):
                yield event
        else:
            async for event in self.chat(message, thread_id, use_knowledge=use_knowledge):
                yield event

    # ── Message / profile helpers ──

    async def get_profile(self, thread_id: str = "default") -> dict:
        return get_profile(thread_id)

    async def get_prd(self, thread_id: str = "default") -> dict | None:
        return _prd_store.get(thread_id)

    async def get_message_history(self, thread_id: str = "default") -> list[dict]:
        return _message_history.get(thread_id, [])

    async def list_sessions(self) -> list[dict]:
        """List all sessions from in-memory state and file backup."""
        sessions = []
        from app.agent.pm.tools import get_profile_store
        store = get_profile_store()
        for sid, profile in store.items():
            if sid == "default":
                continue
            sessions.append({
                "session_id": sid,
                "project_name": profile.get("project_name") or "未命名项目",
                "status": "mining",
                "sufficiency_score": profile.get("sufficiency_score", 0),
                "updated_at": "",
            })
        return sorted(sessions, key=lambda s: s["project_name"])

    async def delete_session(self, thread_id: str) -> bool:
        _session_state.pop(thread_id, None)
        _message_history.pop(thread_id, None)
        _prd_store.pop(thread_id, None)
        remove_profile(thread_id)
        # Also remove file backups
        for f in [f"profile_{thread_id}.json", f"prd_{thread_id}.json"]:
            fp = os.path.join(config.data_dir, f)
            if os.path.exists(fp):
                os.remove(fp)
        return True

    async def cleanup(self):
        await get_mining_agent().close()


def _save_message(thread_id: str, role: str, content: str,
                  event_type: str = "message", meta: dict | None = None):
    if not content.strip():
        return
    if thread_id not in _message_history:
        _message_history[thread_id] = []
    _message_history[thread_id].append({
        "role": role,
        "content": content,
        "event_type": event_type,
        "meta": meta or {},
    })


pm_agent_service = PMAgentService()
