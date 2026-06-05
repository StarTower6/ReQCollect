"""FileDataStore — JSON file fallback when MySQL is unavailable.

Replaces the scattered _save_to_file / _load_from_file logic in
pm_agent_service.py with a unified DataStore implementation.

Directory layout under data_dir (default ./pm_data):
  pm_data/
    sessions/
      {session_id}.json       # session metadata
    profiles/
      {session_id}.json       # requirement profiles
    messages/
      {session_id}.json       # chat messages
    prds/
      {session_id}.json       # generated PRDs (list of versions)
    audit/
      audit_log.json          # append-only audit log
    overview.json             # cached dashboard overview
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import config
from app.db import DataStore


_SESSION_DEFAULTS = {
    "project_name": "",
    "user_id": "default",
    "status": "mining",
    "sufficiency_score": 0.0,
    "is_pinned": False,
    "tags": [],
}

_PROFILE_DEFAULTS = {
    "project_name": "",
    "business_background": "",
    "current_process": "",
    "user_roles": [],
    "business_flow": "",
    "functional_requirements": [],
    "existing_systems": [],
    "non_functional": {},
    "data_scale": "",
    "constraints": [],
    "success_criteria": [],
    "covered_topics": [],
    "pending_questions": [],
    "sufficiency_score": 0.0,
}


class _FileLock:
    """Simple file-level write atomicity via atomic rename."""

    @staticmethod
    def write_json(filepath: Path, data: Any):
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(filepath)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FileDataStore(DataStore):
    """JSON file-backed data store — compatible with MySQLDataStore interface."""

    def __init__(self):
        self._base = Path(config.data_dir)
        self._sessions_dir = self._base / "sessions"
        self._profiles_dir = self._base / "profiles"
        self._messages_dir = self._base / "messages"
        self._prds_dir = self._base / "prds"
        self._audit_file = self._base / "audit" / "audit_log.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self._sessions_dir, self._profiles_dir, self._messages_dir, self._prds_dir, self._audit_file.parent]:
            d.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self._sessions_dir / f"{session_id}.json"

    def _profile_path(self, session_id: str) -> Path:
        return self._profiles_dir / f"{session_id}.json"

    def _messages_path(self, session_id: str) -> Path:
        return self._messages_dir / f"{session_id}.json"

    def _prds_path(self, session_id: str) -> Path:
        return self._prds_dir / f"{session_id}.json"

    def _load_json(self, path: Path) -> Any | None:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load {path}: {e}")
        return None

    # ── Sessions ──

    async def create_session(
        self,
        session_id: str,
        user_id: str = "default",
        project_name: str = "",
    ) -> dict:
        now = _now()
        data = {
            "session_id": session_id,
            "user_id": user_id,
            "project_name": project_name,
            "status": "mining",
            "sufficiency_score": 0.0,
            "is_pinned": False,
            "tags": [],
            "created_at": now,
            "updated_at": now,
        }
        _FileLock.write_json(self._session_path(session_id), data)
        return data

    async def get_session(self, session_id: str) -> dict | None:
        data = self._load_json(self._session_path(session_id))
        return data

    async def list_sessions(
        self,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        sessions = []
        for f in sorted(self._sessions_dir.glob("*.json"), reverse=True):
            data = self._load_json(f)
            if data is None:
                continue
            if user_id and data.get("user_id") != user_id:
                continue
            if status and data.get("status") != status:
                continue
            sessions.append(data)
        # Sort by updated_at desc
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions[offset : offset + limit]

    async def update_session(
        self, session_id: str, **kwargs: Any
    ) -> dict | None:
        path = self._session_path(session_id)
        data = self._load_json(path)
        if data is None:
            return None
        for key, value in kwargs.items():
            data[key] = value
        data["updated_at"] = _now()
        _FileLock.write_json(path, data)
        return data

    async def delete_session(self, session_id: str) -> bool:
        path = self._session_path(session_id)
        if not path.exists():
            return False
        path.unlink(missing_ok=True)
        # Clean up related files
        self._profile_path(session_id).unlink(missing_ok=True)
        self._messages_path(session_id).unlink(missing_ok=True)
        self._prds_path(session_id).unlink(missing_ok=True)
        return True

    # ── Messages ──

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        event_type: str = "message",
        meta: dict | None = None,
    ) -> dict:
        path = self._messages_path(session_id)
        messages = self._load_json(path) or []
        msg = {
            "id": f"msg_{len(messages)}_{session_id[-8:]}" if len(session_id) > 8 else f"msg_{len(messages)}",
            "session_id": session_id,
            "role": role,
            "content": content,
            "event_type": event_type,
            "meta": meta or {},
            "created_at": _now(),
        }
        messages.append(msg)
        _FileLock.write_json(path, messages)

        # Touch session updated_at
        sess = await self.get_session(session_id)
        if sess:
            sess["updated_at"] = _now()
            _FileLock.write_json(self._session_path(session_id), sess)
        return msg

    async def get_message_history(
        self,
        session_id: str,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        path = self._messages_path(session_id)
        messages = self._load_json(path) or []
        return messages[offset : offset + limit]

    # ── Requirement Profiles ──

    async def get_profile(self, session_id: str) -> dict:
        data = self._load_json(self._profile_path(session_id))
        if data is None:
            return dict(_PROFILE_DEFAULTS)
        return {k: data.get(k, v) for k, v in _PROFILE_DEFAULTS.items()}

    async def save_profile(self, session_id: str, profile: dict) -> dict:
        path = self._profile_path(session_id)
        merged = dict(_PROFILE_DEFAULTS)
        merged.update(profile)
        merged["updated_at"] = _now()

        _FileLock.write_json(path, merged)

        # Sync project_name to session
        if merged.get("project_name"):
            await self.update_session(
                session_id,
                project_name=merged["project_name"],
                sufficiency_score=merged.get("sufficiency_score", 0.0),
            )
        return merged

    async def update_profile_field(
        self, session_id: str, field: str, value: Any
    ) -> dict:
        path = self._profile_path(session_id)
        data = self._load_json(path)
        if data is None:
            data = dict(_PROFILE_DEFAULTS)
        data[field] = value
        data["updated_at"] = _now()
        _FileLock.write_json(path, data)
        return data

    # ── PRDs ──

    async def save_prd(
        self,
        session_id: str,
        project_name: str = "",
        mode: str = "one_shot",
        sections: list | None = None,
        markdown: str = "",
    ) -> dict:
        path = self._prds_path(session_id)
        prds = self._load_json(path) or []
        next_version = max((p.get("version", 0) for p in prds), default=0) + 1
        prd = {
            "id": f"prd_{session_id[-8:]}_v{next_version}" if len(session_id) > 8 else f"prd_v{next_version}",
            "session_id": session_id,
            "version": next_version,
            "title": project_name,
            "mode": mode,
            "sections": sections or [],
            "markdown": markdown,
            "created_at": _now(),
        }
        prds.append(prd)
        _FileLock.write_json(path, prds)

        # Mark session as complete
        await self.update_session(session_id, status="complete")
        return prd

    async def get_prd(self, session_id: str, version: int | None = None) -> dict | None:
        prds = self._load_json(self._prds_path(session_id))
        if not prds:
            return None
        if version is not None:
            for p in prds:
                if p.get("version") == version:
                    return p
        return prds[-1]  # latest version

    async def list_prds(self, session_id: str) -> list[dict]:
        prds = self._load_json(self._prds_path(session_id))
        return prds or []

    # ── Dashboard ──

    async def get_dashboard_overview(self) -> dict:
        sessions = []
        for f in self._sessions_dir.glob("*.json"):
            data = self._load_json(f)
            if data:
                sessions.append(data)

        total = len(sessions)
        by_status: dict[str, int] = defaultdict(int)
        scores = []
        prd_count = 0
        msg_count = 0

        for s in sessions:
            by_status[s.get("status", "mining")] += 1
            sc = s.get("sufficiency_score", 0)
            if sc and sc > 0:
                scores.append(sc)

            # Count messages per session
            msgs = self._load_json(self._messages_path(s.get("session_id", "")))
            if msgs:
                msg_count += len(msgs)

        # Count PRDs
        for f in self._prds_dir.glob("*.json"):
            prds = self._load_json(f)
            if prds:
                prd_count += len(prds)

        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        return {
            "total_sessions": total,
            "by_status": dict(by_status),
            "avg_sufficiency": avg_score,
            "total_prds": prd_count,
            "total_messages": msg_count,
        }

    async def get_trend_data(
        self, granularity: str = "day", days: int = 30
    ) -> list[dict]:
        sessions = await self.list_sessions(limit=10000)
        now = datetime.now(timezone.utc)
        from collections import Counter

        session_counts: Counter[str] = Counter()
        prd_counts: Counter[str] = Counter()

        for s in sessions:
            created = s.get("created_at", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created)
                    if (now - dt).days > days:
                        continue
                    key = self._truncate_date(dt, granularity)
                    session_counts[key] += 1
                except ValueError:
                    pass

            # Check for PRDs
            prds = await self.list_prds(s.get("session_id", ""))
            for p in prds:
                pc = p.get("created_at", "")
                if pc:
                    try:
                        dt = datetime.fromisoformat(pc)
                        if (now - dt).days > days:
                            continue
                        key = self._truncate_date(dt, granularity)
                        prd_counts[key] += 1
                    except ValueError:
                        pass

        all_dates = sorted(set(list(session_counts.keys()) + list(prd_counts.keys())))
        return [
            {
                "date": d,
                "sessions": session_counts.get(d, 0),
                "prds": prd_counts.get(d, 0),
            }
            for d in all_dates
        ]

    @staticmethod
    def _truncate_date(dt: datetime, granularity: str) -> str:
        if granularity == "day":
            return dt.strftime("%Y-%m-%d")
        elif granularity == "week":
            # ISO week
            iso = dt.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        elif granularity == "month":
            return dt.strftime("%Y-%m")
        return dt.strftime("%Y-%m-%d")

    # ── Audit ──

    async def log_audit(
        self,
        action: str,
        user_id: str = "",
        session_id: str = "",
        detail: dict | None = None,
        ip_address: str = "",
    ) -> None:
        logs = self._load_json(self._audit_file) or []
        logs.append({
            "id": len(logs) + 1,
            "user_id": user_id,
            "session_id": session_id,
            "action": action,
            "detail": detail or {},
            "ip_address": ip_address,
            "created_at": _now(),
        })
        _FileLock.write_json(self._audit_file, logs)

    # ── Health ──

    async def health(self) -> dict:
        return {"backend": "file", "status": "ok"}
