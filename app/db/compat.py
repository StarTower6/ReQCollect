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
import uuid
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
        self._users_file = self._base / "users" / "users.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self._sessions_dir, self._profiles_dir, self._messages_dir,
                  self._prds_dir, self._audit_file.parent, self._users_file.parent]:
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
        workspace_id: str | None = None,
    ) -> dict:
        now = _now()
        data = {
            "session_id": session_id,
            "workspace_id": workspace_id or "",
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
        workspace_id: str | None = None,
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
            if workspace_id and data.get("workspace_id") != workspace_id:
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

    # ── Users ──

    async def create_user(
        self,
        username: str,
        password_hash: str,
        display_name: str = "",
        email: str = "",
        department: str = "",
        role: str = "business",
        source: str = "local",
    ) -> dict:
        users = self._load_json(self._users_file) or []
        # Check duplicate
        for u in users:
            if u.get("username") == username:
                raise ValueError(f"Username '{username}' already exists")
        now = _now()
        user = {
            "id": uuid.uuid4().hex[:16],
            "username": username,
            "display_name": display_name or username,
            "email": email,
            "department": department,
            "role": role,
            "source": source,
            "password_hash": password_hash,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        users.append(user)
        _FileLock.write_json(self._users_file, users)
        return {k: v for k, v in user.items() if k != "password_hash"}

    async def get_user_by_username(self, username: str) -> dict | None:
        users = self._load_json(self._users_file) or []
        for u in users:
            if u.get("username") == username:
                return dict(u)
        return None

    async def get_user_by_id(self, user_id: str) -> dict | None:
        users = self._load_json(self._users_file) or []
        for u in users:
            if u.get("id") == user_id:
                return dict(u)
        return None

    async def list_users(self) -> list[dict]:
        users = self._load_json(self._users_file) or []
        return [
            {k: v for k, v in u.items() if k != "password_hash"}
            for u in users
        ]

    async def update_user(self, user_id: str, **kwargs) -> dict | None:
        users = self._load_json(self._users_file) or []
        for i, u in enumerate(users):
            if u.get("id") == user_id:
                for key, value in kwargs.items():
                    u[key] = value
                u["updated_at"] = _now()
                _FileLock.write_json(self._users_file, users)
                return {k: v for k, v in u.items() if k != "password_hash"}
        return None

    async def delete_user(self, user_id: str) -> bool:
        users = self._load_json(self._users_file) or []
        for i, u in enumerate(users):
            if u.get("id") == user_id:
                users.pop(i)
                _FileLock.write_json(self._users_file, users)
                return True
        return False

    # ── Import Records ──

    def _imports_path(self, session_id: str) -> Path:
        p = self._base / "imports" / session_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _imports_index(self, session_id: str) -> Path:
        return self._imports_path(session_id) / "_index.json"

    async def save_import_record(
        self,
        session_id: str,
        filename: str,
        file_path: str,
        fields_filled: list[str] | None = None,
    ) -> dict:
        idx_path = self._imports_index(session_id)
        records = self._load_json(idx_path) or []
        now = _now()
        record = {
            "id": len(records) + 1,
            "session_id": session_id,
            "filename": filename,
            "file_path": file_path,
            "fields_filled": fields_filled or [],
            "created_at": now,
        }
        records.append(record)
        self._imports_index(session_id).parent.mkdir(parents=True, exist_ok=True)
        _FileLock.write_json(idx_path, records)
        return record

    async def get_import_records(self, session_id: str) -> list[dict]:
        return self._load_json(self._imports_index(session_id)) or []

    # ── Workspaces ──

    def _workspaces_path(self) -> Path:
        p = self._base / "workspaces"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _workspace_file(self, ws_id: str) -> Path:
        return self._workspaces_path() / f"{ws_id}.json"

    def _workspaces_index(self) -> Path:
        return self._workspaces_path() / "_index.json"

    async def create_workspace(
        self,
        name: str,
        created_by: str,
        code: str = "",
        description: str = "",
    ) -> dict:
        import uuid
        now = _now()
        ws = {
            "id": uuid.uuid4().hex[:16],
            "name": name,
            "code": code,
            "description": description,
            "created_by": created_by,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        _FileLock.write_json(self._workspace_file(ws["id"]), ws)
        # Update index
        index = self._load_json(self._workspaces_index()) or []
        index.append(ws["id"])
        _FileLock.write_json(self._workspaces_index(), index)
        return dict(ws)

    async def get_workspace(self, workspace_id: str) -> dict | None:
        return self._load_json(self._workspace_file(workspace_id))

    async def list_workspaces(self, user_id: str | None = None) -> list[dict]:
        workspaces = []
        for f in sorted(self._workspaces_path().glob("*.json")):
            if f.name == "_index.json":
                continue
            data = self._load_json(f)
            if data and data.get("is_active", True):
                workspaces.append(data)
        workspaces.sort(key=lambda w: w.get("updated_at", ""), reverse=True)
        return workspaces

    async def update_workspace(self, workspace_id: str, **kwargs) -> dict | None:
        ws = await self.get_workspace(workspace_id)
        if ws is None:
            return None
        for key, value in kwargs.items():
            ws[key] = value
        ws["updated_at"] = _now()
        _FileLock.write_json(self._workspace_file(workspace_id), ws)
        return dict(ws)

    async def delete_workspace(self, workspace_id: str) -> bool:
        ws_file = self._workspace_file(workspace_id)
        if not ws_file.exists():
            return False
        ws_file.unlink(missing_ok=True)
        # Remove from index
        index = self._load_json(self._workspaces_index()) or []
        if workspace_id in index:
            index.remove(workspace_id)
            _FileLock.write_json(self._workspaces_index(), index)
        # Orphan sessions: clear workspace_id (don't delete them)
        for f in self._sessions_dir.glob("*.json"):
            data = self._load_json(f)
            if data and data.get("workspace_id") == workspace_id:
                data["workspace_id"] = ""
                data["updated_at"] = _now()
                _FileLock.write_json(f, data)
        return True

    # ── Workspace Files ──

    async def list_workspace_files(self, workspace_id: str, pattern: str = "*", max_results: int = 50) -> list[dict]:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).list_files(pattern, max_results)

    async def add_workspace_file(self, workspace_id: str, filename: str, content: bytes, uploaded_by: str = "") -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).upload_file(filename, content, uploaded_by)

    async def read_workspace_file(self, workspace_id: str, file_path: str, max_chars: int = 8000) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).read_file(file_path, max_chars)

    async def remove_workspace_file(self, workspace_id: str, file_path: str) -> bool:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).delete_file(file_path)

    async def search_workspace_files(self, workspace_id: str, query: str, file_pattern: str = "*.md", max_results: int = 10) -> list[dict]:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).search_files(query, file_pattern, max_results)

    async def write_workspace_file(self, workspace_id: str, file_path: str, content: str) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).write_file(file_path, content)

    async def get_workspace_files_info(self, workspace_id: str) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).get_info()

    async def link_workspace_directory(self, workspace_id: str, dir_path: str) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).link_directory(dir_path)

    async def unlink_workspace_directory(self, workspace_id: str) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).unlink_directory()

    async def sync_workspace_files(self, workspace_id: str) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).sync_linked()

    async def get_workspace_linked_status(self, workspace_id: str) -> dict:
        from app.core.workspace_files import WorkspaceFileManager
        return WorkspaceFileManager(workspace_id).get_linked_status()

    # ── Wiki Pages ──

    def _wiki_path(self, workspace_id: str) -> Path:
        p = self._base / "wiki" / workspace_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _wiki_file(self, workspace_id: str, page_id: str) -> Path:
        return self._wiki_path(workspace_id) / f"{page_id}.json"

    async def create_wiki_page(
        self,
        workspace_id: str,
        title: str,
        content: str = "",
        created_by: str = "",
    ) -> dict:
        import uuid
        now = _now()
        page_id = uuid.uuid4().hex[:16]
        data = {
            "id": page_id,
            "workspace_id": workspace_id,
            "title": title,
            "content": content,
            "created_by": created_by,
            "updated_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
        _FileLock.write_json(self._wiki_file(workspace_id, page_id), data)
        return dict(data)

    async def get_wiki_page(self, page_id: str) -> dict | None:
        wiki_base = self._base / "wiki"
        if not wiki_base.exists():
            return None
        for ws_dir in wiki_base.iterdir():
            if not ws_dir.is_dir():
                continue
            f = ws_dir / f"{page_id}.json"
            if f.exists():
                return self._load_json(f)
        return None

    async def list_wiki_pages(self, workspace_id: str) -> list[dict]:
        pages = []
        ws_dir = self._base / "wiki" / workspace_id
        if not ws_dir.exists():
            return pages
        for f in sorted(ws_dir.glob("*.json"), reverse=True):
            data = self._load_json(f)
            if data:
                pages.append(data)
        pages.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return pages

    async def resolve_wiki_title(self, workspace_id: str, title: str) -> dict | None:
        """Resolve a wiki page title to page dict. Returns None if not found."""
        pages = await self.list_wiki_pages(workspace_id)
        for p in pages:
            if p.get("title", "").strip() == title.strip():
                return p
        return None

    async def update_wiki_page(self, page_id: str, **kwargs) -> dict | None:
        page = await self.get_wiki_page(page_id)
        if page is None:
            return None
        ws_id = page.get("workspace_id", "")
        for key, value in kwargs.items():
            page[key] = value
        page["updated_at"] = _now()
        _FileLock.write_json(self._wiki_file(ws_id, page_id), page)
        return dict(page)

    async def delete_wiki_page(self, page_id: str) -> bool:
        page = await self.get_wiki_page(page_id)
        if page is None:
            return False
        ws_id = page.get("workspace_id", "")
        f = self._wiki_file(ws_id, page_id)
        if f.exists():
            f.unlink(missing_ok=True)
            # Cascade: remove all wiki links for this page
            await self.delete_links_for_ref(page_id, "wiki")
            return True
        return False

    # ── Wiki Links / File Links ──

    def _wiki_links_path(self) -> Path:
        p = self._base / "wiki" / "_links"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def _link_filename(source_ref: str, target_ref: str) -> str:
        """Create a filesystem-safe link filename from refs that may contain path separators."""
        safe_src = source_ref.replace("/", "_").replace(":", "_")
        safe_tgt = target_ref.replace("/", "_").replace(":", "_")
        return f"{safe_src}--{safe_tgt}.json"

    @staticmethod
    def _link_glob(source_ref: str) -> str:
        return f"{source_ref.replace('/', '_').replace(':', '_')}--*.json"

    @staticmethod
    def _backlink_glob(target_ref: str) -> str:
        return f"*--{target_ref.replace('/', '_').replace(':', '_')}.json"

    async def get_links(self, workspace_id: str, ref: str, ref_type: str = "wiki",
                        direction: str = "outgoing") -> list[dict]:
        """Get links from/to a reference in a workspace.

        When workspace_id is empty string (backward compat path), skip workspace_id filtering.
        """
        links_dir = self._base / "wiki" / "_links"
        if not links_dir.exists():
            return []
        result = []
        for f in links_dir.rglob("*.json"):
            if not f.is_file():
                continue
            data = self._load_json(f)
            if data is None:
                continue
            if workspace_id and data.get("workspace_id", "") != workspace_id:
                continue
            # Normalize old format (source_page_id) to new format (source_ref)
            if "source_page_id" in data and "source_ref" not in data:
                data["source_ref"] = data.pop("source_page_id")
                data["source_type"] = data.get("source_type", "wiki")
            if "target_page_id" in data and "target_ref" not in data:
                data["target_ref"] = data.pop("target_page_id")
                data["target_type"] = data.get("target_type", "wiki")
            # Check ref match using decoded refs
            check_ref = data.get("source_ref" if direction == "outgoing" else "target_ref")
            check_type = data.get("source_type" if direction == "outgoing" else "target_type")
            if check_ref == ref and check_type == ref_type:
                result.append(data)
        return result

    async def save_links(self, workspace_id: str,
                         source_ref: str, source_type: str,
                         targets: list[tuple[str, str]],
                         link_type: str = "reference") -> None:
        """Full-replace: remove old outgoing links, insert new ones."""
        links_dir = self._base / "wiki" / "_links"
        links_dir.mkdir(parents=True, exist_ok=True)
        # Remove old outgoing links from this source
        for f in list(links_dir.rglob(self._link_glob(source_ref))):
            f.unlink(missing_ok=True)
        # Create new links
        for target_ref, target_type in targets:
            data = {
                "source_ref": source_ref,
                "source_type": source_type,
                "target_ref": target_ref,
                "target_type": target_type,
                "link_type": link_type,
                "workspace_id": workspace_id,
            }
            _FileLock.write_json(
                links_dir / self._link_filename(source_ref, target_ref), data
            )

    async def get_graph_edges(self, workspace_id: str) -> list[dict]:
        """Get ALL links in a workspace."""
        links_dir = self._base / "wiki" / "_links"
        if not links_dir.exists():
            return []
        edges = []
        for f in links_dir.rglob("*.json"):
            if not f.is_file():
                continue
            data = self._load_json(f)
            if data and data.get("workspace_id", "") == workspace_id:
                # Normalize old format
                if "source_page_id" in data and "source_ref" not in data:
                    data["source_ref"] = data.pop("source_page_id")
                    data["source_type"] = data.get("source_type", "wiki")
                if "target_page_id" in data and "target_ref" not in data:
                    data["target_ref"] = data.pop("target_page_id")
                    data["target_type"] = data.get("target_type", "wiki")
                edges.append({
                    "from": f"{data['source_type']}:{data['source_ref']}",
                    "to": f"{data['target_type']}:{data['target_ref']}",
                    "title": data.get("link_type", "reference"),
                })
        return edges

    async def delete_links_for_ref(self, ref: str, ref_type: str = "wiki") -> None:
        """Remove all links (outgoing + incoming) for a reference."""
        links_dir = self._base / "wiki" / "_links"
        if not links_dir.exists():
            return
        for f in list(links_dir.rglob("*.json")):
            if not f.is_file():
                continue
            data = self._load_json(f)
            if data is None:
                continue
            if "source_page_id" in data and "source_ref" not in data:
                data["source_ref"] = data.pop("source_page_id")
                data["source_type"] = data.get("source_type", "wiki")
            if "target_page_id" in data and "target_ref" not in data:
                data["target_ref"] = data.pop("target_page_id")
                data["target_type"] = data.get("target_type", "wiki")
            if (data.get("source_ref") == ref and data.get("source_type") == ref_type) or \
               (data.get("target_ref") == ref and data.get("target_type") == ref_type):
                f.unlink(missing_ok=True)

    # ── Backward compat aliases ──
    async def get_wiki_links(self, page_id: str) -> list[dict]:
        return await self.get_links("", page_id, "wiki", "outgoing")

    async def get_wiki_backlinks(self, page_id: str) -> list[dict]:
        return await self.get_links("", page_id, "wiki", "incoming")

    async def save_wiki_links(
        self, source_page_id: str, target_ids: list[str], link_type: str = "reference"
    ) -> None:
        targets = [(tid, "wiki") for tid in target_ids]
        await self.save_links("", source_page_id, "wiki", targets, link_type)

    async def delete_wiki_links_for_page(self, page_id: str) -> None:
        await self.delete_links_for_ref(page_id, "wiki")

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
    # ── Requirement Proposals ──

    @property
    def _proposals_file(self) -> Path:
        return self._base / "proposals.json"

    async def create_proposal(
        self,
        workspace_id: str,
        *,
        title: str = "",
        source_session_id: str = "",
        submitter_id: str = "",
        background: str = "",
        pain_points: list | None = None,
        desired_outcome: str = "",
        scope_note: str = "",
        urgency: str = "medium",
        priority: str = "P2",
        tags: list | None = None,
        status: str = "pending_review",
    ) -> dict:
        proposals = self._load_json(self._proposals_file) or []
        import uuid
        now = _now()
        p = {
            "id": uuid.uuid4().hex[:16],
            "workspace_id": workspace_id,
            "source_session_id": source_session_id,
            "submitter_id": submitter_id,
            "title": title,
            "background": background,
            "pain_points": pain_points or [],
            "desired_outcome": desired_outcome,
            "scope_note": scope_note,
            "urgency": urgency,
            "priority": priority,
            "ai_assessment": "",
            "status": status,
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
        }
        proposals.append(p)
        _FileLock.write_json(self._proposals_file, proposals)
        return dict(p)

    async def get_proposal(self, proposal_id: str) -> dict | None:
        proposals = self._load_json(self._proposals_file) or []
        for p in proposals:
            if p["id"] == proposal_id:
                return dict(p)
        return None

    async def list_proposals(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        urgency: str | None = None,
        priority: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        proposals = self._load_json(self._proposals_file) or []
        filtered = [
            p for p in proposals
            if p["workspace_id"] == workspace_id
            and (status is None or p.get("status") == status)
            and (urgency is None or p.get("urgency") == urgency)
            and (priority is None or p.get("priority") == priority)
        ]
        filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [dict(p) for p in filtered[offset : offset + limit]]

    async def update_proposal(self, proposal_id: str, **kwargs) -> dict | None:
        proposals = self._load_json(self._proposals_file) or []
        for i, p in enumerate(proposals):
            if p["id"] == proposal_id:
                for key, value in kwargs.items():
                    p[key] = value
                p["updated_at"] = _now()
                proposals[i] = p
                _FileLock.write_json(self._proposals_file, proposals)
                return dict(p)
        return None

    async def delete_proposal(self, proposal_id: str) -> bool:
        proposals = self._load_json(self._proposals_file) or []
        for i, p in enumerate(proposals):
            if p["id"] == proposal_id:
                del proposals[i]
                _FileLock.write_json(self._proposals_file, proposals)
                return True
        return False

    async def count_proposals(self, workspace_id: str) -> dict:
        proposals = self._load_json(self._proposals_file) or []
        counts: dict[str, int] = {}
        for p in proposals:
            if p["workspace_id"] == workspace_id:
                key = p.get("status", "unknown")
                counts[key] = counts.get(key, 0) + 1
        return counts

    def _load_all_prds(self) -> list[dict]:
        """Load all PRDs across all sessions, enriched with workspace_id."""
        all_prds = []
        for f in self._prds_dir.glob("*.json"):
            if not f.exists():
                continue
            prds = self._load_json(f)
            if not prds:
                continue
            for p in prds:
                sid = p.get("session_id", "")
                if sid:
                    sess = self._load_json(self._session_path(sid))
                    if sess:
                        p["workspace_id"] = sess.get("workspace_id", "")
                all_prds.append(p)
        return all_prds

    async def get_prd_by_id(self, prd_id: str) -> dict | None:
        prds = self._load_all_prds()
        for p in prds:
            if p.get("id") == prd_id:
                return p
        return None

    async def list_prds_by_workspace(self, workspace_id: str) -> list[dict]:
        prds = self._load_all_prds()
        return sorted(
            [p for p in prds if p.get("workspace_id") == workspace_id],
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )

    async def update_prd(self, prd_id: str, **kwargs) -> dict | None:
        """Update PRD fields. Returns updated PRD or None."""
        # Find and update in-memory, then persist
        all_prds = self._load_all_prds()
        updated = None
        for p in all_prds:
            if p.get("id") == prd_id:
                for key, val in kwargs.items():
                    if val is not None:
                        p[key] = val
                updated = p
                break
        if updated is None:
            return None
        # Persist back to the session's PRD file
        sid = updated.get("session_id", "")
        if sid:
            path = self._prds_path(sid)
            existing = self._load_json(path) or []
            for i, ep in enumerate(existing):
                if ep.get("id") == prd_id:
                    existing[i] = updated
                    break
            _FileLock.write_json(path, existing)
        return updated

