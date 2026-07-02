"""MySQLDataStore — async MySQL CRUD via SQLAlchemy + asyncmy."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import func, select, text, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import DataStore
from app.db.database import get_session_factory
from app.db.exceptions import SessionNotFoundError
from app.db.models import (
    AuditLog,
    ChatMessage,
    GeneratedPRD,
    RequirementProfile,
    RequirementProposal,
    Session,
    User,
    WikiLink,
    WikiPage,
    Workspace,
)


class MySQLDataStore(DataStore):
    """MySQL-backed data store using async SQLAlchemy + asyncmy."""

    async def _get_session(self) -> AsyncSession:
        factory = get_session_factory()
        if factory is None:
            raise RuntimeError("MySQL session factory not initialized")
        return factory()

    # ── Users ──

    async def _ensure_default_user(self) -> str:
        """Get or create the default user. Returns user_id."""
        async with await self._get_session() as s:
            result = await s.execute(
                select(User).where(User.username == "default")
            )
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    username="default",
                    display_name="Default User",
                    role="business",
                    source="local",
                )
                s.add(user)
                await s.commit()
                await s.refresh(user)
            return user.id

    async def _get_or_create_user(self, user_id: str, session_async_session: AsyncSession | None = None) -> str:
        """Get user by id, creating as default if missing.

        Can accept an existing async session for transactional consistency.
        """
        if session_async_session is not None:
            result = await session_async_session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    id=user_id,
                    username=user_id,
                    display_name=user_id,
                    role="business",
                    source="local",
                )
                session_async_session.add(user)
                await session_async_session.flush()
            return user.id

        async with await self._get_session() as s:
            result = await s.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    id=user_id,
                    username=user_id,
                    display_name=user_id,
                    role="business",
                    source="local",
                )
                s.add(user)
                await s.commit()
            return user.id

    # New User CRUD — replaces the legacy _ensure_default_user pattern

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
        async with await self._get_session() as s:
            # Check duplicate
            result = await s.execute(
                select(User).where(User.username == username)
            )
            if result.scalar_one_or_none():
                raise ValueError(f"Username '{username}' already exists")
            user = User(
                username=username,
                display_name=display_name or username,
                email=email,
                department=department,
                role=role,
                source=source,
                password_hash=password_hash,
            )
            s.add(user)
            await s.commit()
            await s.refresh(user)
            return {"id": user.id, "username": user.username,
                    "display_name": user.display_name, "email": user.email,
                    "department": user.department, "role": user.role,
                    "source": user.source, "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else "",
                    "updated_at": user.updated_at.isoformat() if user.updated_at else ""}

    async def get_user_by_username(self, username: str) -> dict | None:
        async with await self._get_session() as s:
            result = await s.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return {"id": user.id, "username": user.username,
                    "display_name": user.display_name, "email": user.email,
                    "department": user.department,                    "role": user.role,
                    "source": user.source, "is_active": user.is_active,
                    "password_hash": user.password_hash or "",
                    "created_at": user.created_at.isoformat() if user.created_at else "",
                    "updated_at": user.updated_at.isoformat() if user.updated_at else ""}

    async def get_user_by_id(self, user_id: str) -> dict | None:
        async with await self._get_session() as s:
            result = await s.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return {"id": user.id, "username": user.username,
                    "display_name": user.display_name, "email": user.email,
                    "department": user.department, "role": user.role,
                    "source": user.source, "is_active": user.is_active,
                    "password_hash": user.password_hash or "",
                    "created_at": user.created_at.isoformat() if user.created_at else "",
                    "updated_at": user.updated_at.isoformat() if user.updated_at else ""}

    async def list_users(self) -> list[dict]:
        async with await self._get_session() as s:
            result = await s.execute(select(User).order_by(User.created_at.desc()))
            users = result.scalars().all()
            return [{"id": u.id, "username": u.username,
                     "display_name": u.display_name, "email": u.email,
                     "department": u.department, "role": u.role,
                     "source": u.source, "is_active": u.is_active,
                     "created_at": u.created_at.isoformat() if u.created_at else "",
                     "updated_at": u.updated_at.isoformat() if u.updated_at else ""}
                    for u in users]

    async def update_user(self, user_id: str, **kwargs) -> dict | None:
        async with await self._get_session() as s:
            result = await s.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return None
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            user.updated_at = datetime.now(timezone.utc)
            await s.commit()
            return {"id": user.id, "username": user.username,
                    "display_name": user.display_name, "email": user.email,
                    "department": user.department, "role": user.role,
                    "source": user.source, "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else "",
                    "updated_at": user.updated_at.isoformat() if user.updated_at else ""}


    async def delete_user(self, user_id: str) -> bool:
        async with await self._get_session() as s:
            result = await s.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return False
            await s.delete(user)
            await s.commit()
            return True

    # ── Import Records ──

    async def save_import_record(
        self,
        session_id: str,
        filename: str,
        file_path: str,
        fields_filled: list[str] | None = None,
    ) -> dict:
        return {
            "id": 1,  # placeholder for MySQL
            "session_id": session_id,
            "filename": filename,
            "file_path": file_path,
            "fields_filled": fields_filled or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_import_records(self, session_id: str) -> list[dict]:
        return []

    # ── Workspaces ──

    async def create_workspace(
        self,
        name: str,
        created_by: str,
        code: str = "",
        description: str = "",
    ) -> dict:
        async with await self._get_session() as s:
            ws = Workspace(
                name=name, code=code,
                description=description, created_by=created_by,
            )
            s.add(ws)
            await s.commit()
            await s.refresh(ws)
            return {
                "id": ws.id, "name": ws.name, "code": ws.code or "",
                "description": ws.description or "", "created_by": ws.created_by,
                "is_active": ws.is_active,
                "created_at": ws.created_at.isoformat() if ws.created_at else "",
                "updated_at": ws.updated_at.isoformat() if ws.updated_at else "",
            }

    async def get_workspace(self, workspace_id: str) -> dict | None:
        async with await self._get_session() as s:
            r = await s.execute(select(Workspace).where(Workspace.id == workspace_id))
            ws = r.scalar_one_or_none()
            if ws is None:
                return None
            return {
                "id": ws.id, "name": ws.name, "code": ws.code or "",
                "description": ws.description or "", "created_by": ws.created_by,
                "is_active": ws.is_active,
                "created_at": ws.created_at.isoformat() if ws.created_at else "",
                "updated_at": ws.updated_at.isoformat() if ws.updated_at else "",
            }

    async def list_workspaces(self, user_id: str | None = None) -> list[dict]:
        async with await self._get_session() as s:
            r = await s.execute(
                select(Workspace).where(Workspace.is_active == True)
                .order_by(Workspace.updated_at.desc())
            )
            wss = r.scalars().all()
            return [{
                "id": ws.id, "name": ws.name, "code": ws.code or "",
                "description": ws.description or "", "created_by": ws.created_by,
                "is_active": ws.is_active,
                "created_at": ws.created_at.isoformat() if ws.created_at else "",
                "updated_at": ws.updated_at.isoformat() if ws.updated_at else "",
            } for ws in wss]

    async def update_workspace(self, workspace_id: str, **kwargs) -> dict | None:
        async with await self._get_session() as s:
            r = await s.execute(select(Workspace).where(Workspace.id == workspace_id))
            ws = r.scalar_one_or_none()
            if ws is None:
                return None
            for key, value in kwargs.items():
                if hasattr(ws, key):
                    setattr(ws, key, value)
            ws.updated_at = datetime.now(timezone.utc)
            await s.commit()
            return {
                "id": ws.id, "name": ws.name, "code": ws.code or "",
                "description": ws.description or "", "created_by": ws.created_by,
                "is_active": ws.is_active,
                "created_at": ws.created_at.isoformat() if ws.created_at else "",
                "updated_at": ws.updated_at.isoformat() if ws.updated_at else "",
            }

    async def delete_workspace(self, workspace_id: str) -> bool:
        async with await self._get_session() as s:
            r = await s.execute(select(Workspace).where(Workspace.id == workspace_id))
            ws = r.scalar_one_or_none()
            if ws is None:
                return False
            await s.delete(ws)
            # Orphan sessions: clear workspace_id (don't delete them)
            await s.execute(
                update(Session)
                .where(Session.workspace_id == workspace_id)
                .values(workspace_id="", updated_at=datetime.now(timezone.utc))
            )
            await s.commit()
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

    async def create_wiki_page(
        self,
        workspace_id: str,
        title: str,
        content: str = "",
        created_by: str = "",
    ) -> dict:
        async with await self._get_session() as s:
            page = WikiPage(
                workspace_id=workspace_id,
                title=title,
                content=content,
                created_by=created_by,
                updated_by=created_by,
            )
            s.add(page)
            await s.commit()
            await s.refresh(page)
            return page.to_dict()

    async def get_wiki_page(self, page_id: str) -> dict | None:
        async with await self._get_session() as s:
            r = await s.execute(select(WikiPage).where(WikiPage.id == page_id))
            page = r.scalar_one_or_none()
            return page.to_dict() if page else None

    async def list_wiki_pages(self, workspace_id: str) -> list[dict]:
        async with await self._get_session() as s:
            r = await s.execute(
                select(WikiPage)
                .where(WikiPage.workspace_id == workspace_id)
                .order_by(WikiPage.updated_at.desc())
            )
            return [p.to_dict() for p in r.scalars().all()]

    async def resolve_wiki_title(self, workspace_id: str, title: str) -> dict | None:
        """Resolve a wiki page title to page dict. Returns None if not found."""
        async with await self._get_session() as s:
            r = await s.execute(
                select(WikiPage)
                .where(WikiPage.workspace_id == workspace_id)
                .where(WikiPage.title == title.strip())
                .limit(1)
            )
            page = r.scalar_one_or_none()
            return page.to_dict() if page else None

    async def update_wiki_page(self, page_id: str, **kwargs) -> dict | None:
        async with await self._get_session() as s:
            r = await s.execute(select(WikiPage).where(WikiPage.id == page_id))
            page = r.scalar_one_or_none()
            if page is None:
                return None
            for key, value in kwargs.items():
                if hasattr(page, key):
                    setattr(page, key, value)
            page.updated_at = datetime.now(timezone.utc)
            await s.commit()
            await s.refresh(page)
            return page.to_dict()

    async def delete_wiki_page(self, page_id: str) -> bool:
        async with await self._get_session() as s:
            r = await s.execute(select(WikiPage).where(WikiPage.id == page_id))
            page = r.scalar_one_or_none()
            if page is None:
                return False
            # Cascade: remove all wiki links for this page
            await s.execute(
                delete(WikiLink).where(
                    (WikiLink.source_ref == page_id) |
                    (WikiLink.target_ref == page_id)
                )
            )
            await s.delete(page)
            await s.commit()
            return True

    # ── Wiki Links / File Links ──

    async def get_wiki_links(self, page_id: str) -> list[dict]:
        """DEPRECATED: Use get_links(). Kept for backward compat."""
        return await self.get_links("", page_id, "wiki", "outgoing")

    async def get_wiki_backlinks(self, page_id: str) -> list[dict]:
        """DEPRECATED: Use get_links(). Kept for backward compat."""
        return await self.get_links("", page_id, "wiki", "incoming")

    async def save_wiki_links(
        self, source_page_id: str, target_ids: list[str], link_type: str = "reference"
    ) -> None:
        """DEPRECATED: Use save_links(). Kept for backward compat."""
        targets = [(tid, "wiki") for tid in target_ids]
        await self.save_links("", source_page_id, "wiki", targets, link_type)

    async def delete_wiki_links_for_page(self, page_id: str) -> None:
        """DEPRECATED: Use delete_links_for_ref(). Kept for backward compat."""
        await self.delete_links_for_ref(page_id, "wiki")

    async def get_links(self, workspace_id: str, ref: str, ref_type: str = "wiki",
                        direction: str = "outgoing") -> list[dict]:
        async with await self._get_session() as s:
            from sqlalchemy import and_
            if direction == "outgoing":
                where = and_(WikiLink.source_ref == ref, WikiLink.source_type == ref_type)
            else:
                where = and_(WikiLink.target_ref == ref, WikiLink.target_type == ref_type)
            if workspace_id:
                where = and_(where, WikiLink.workspace_id == workspace_id)
            stmt = select(WikiLink).where(where)
            result = await s.execute(stmt)
            return [link.to_dict() for link in result.scalars().all()]

    async def save_links(self, workspace_id: str,
                         source_ref: str, source_type: str,
                         targets: list[tuple[str, str]],
                         link_type: str = "reference") -> None:
        async with await self._get_session() as s:
            # Remove old outgoing
            await s.execute(
                delete(WikiLink).where(
                    WikiLink.source_ref == source_ref,
                    WikiLink.source_type == source_type,
                    WikiLink.workspace_id == workspace_id,
                )
            )
            # Insert new
            for target_ref, target_type in targets:
                s.add(WikiLink(
                    source_ref=source_ref, source_type=source_type,
                    target_ref=target_ref, target_type=target_type,
                    link_type=link_type, workspace_id=workspace_id,
                ))
            await s.commit()

    async def get_graph_edges(self, workspace_id: str) -> list[dict]:
        """Get ALL links in a workspace for graph visualization."""
        async with await self._get_session() as s:
            result = await s.execute(
                select(WikiLink).where(WikiLink.workspace_id == workspace_id)
            )
            links = result.scalars().all()
            return [{
                "from": f"{link.source_type}:{link.source_ref}",
                "to": f"{link.target_type}:{link.target_ref}",
                "title": link.link_type,
            } for link in links]

    async def delete_links_for_ref(self, ref: str, ref_type: str = "wiki") -> None:
        async with await self._get_session() as s:
            from sqlalchemy import or_
            await s.execute(
                delete(WikiLink).where(
                    or_(
                        and_(WikiLink.source_ref == ref, WikiLink.source_type == ref_type),
                        and_(WikiLink.target_ref == ref, WikiLink.target_type == ref_type),
                    )
                )
            )
            await s.commit()

    # ── Sessions ──

    async def create_session(
        self,
        session_id: str,
        user_id: str = "default",
        project_name: str = "",
        workspace_id: str | None = None,
    ) -> dict:
        async with await self._get_session() as s:
            await self._get_or_create_user(user_id, session_async_session=s)
            session = Session(
                id=session_id,
                workspace_id=workspace_id or "",
                user_id=user_id,
                project_name=project_name,
            )
            s.add(session)
            await s.commit()
            await s.refresh(session)
            return session.to_dict()

    async def get_session(self, session_id: str) -> dict | None:
        async with await self._get_session() as s:
            result = await s.execute(select(Session).where(Session.id == session_id))
            session = result.scalar_one_or_none()
            return session.to_dict() if session else None

    async def list_sessions(
        self,
        user_id: str | None = None,
        status: str | None = None,
        workspace_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        async with await self._get_session() as s:
            stmt = select(Session)
            if user_id:
                stmt = stmt.where(Session.user_id == user_id)
            if status:
                stmt = stmt.where(Session.status == status)
            if workspace_id:
                stmt = stmt.where(Session.workspace_id == workspace_id)
            stmt = stmt.order_by(Session.updated_at.desc()).limit(limit).offset(offset)
            result = await s.execute(stmt)
            sessions = result.scalars().all()
            return [s.to_dict() for s in sessions]

    async def update_session(self, session_id: str, **kwargs: Any) -> dict | None:
        async with await self._get_session() as s:
            result = await s.execute(select(Session).where(Session.id == session_id))
            session = result.scalar_one_or_none()
            if session is None:
                return None
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.updated_at = datetime.now(timezone.utc)
            await s.commit()
            await s.refresh(session)
            return session.to_dict()

    async def delete_session(self, session_id: str) -> bool:
        async with await self._get_session() as s:
            result = await s.execute(select(Session).where(Session.id == session_id))
            session = result.scalar_one_or_none()
            if session is None:
                return False
            await s.delete(session)
            await s.commit()
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
        async with await self._get_session() as s:
            msg = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                event_type=event_type,
                meta=meta or {},
            )
            s.add(msg)
            # Update session's updated_at
            await s.execute(
                update(Session)
                .where(Session.id == session_id)
                .values(updated_at=datetime.now(timezone.utc))
            )
            await s.commit()
            await s.refresh(msg)
            return msg.to_dict()

    async def get_message_history(
        self,
        session_id: str,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        async with await self._get_session() as s:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
            result = await s.execute(stmt)
            messages = result.scalars().all()
            return [m.to_dict() for m in messages]

    # ── Requirement Profiles ──

    async def get_profile(self, session_id: str) -> dict:
        """Get profile. Returns defaults if none exists (idempotent)."""
        async with await self._get_session() as s:
            result = await s.execute(
                select(RequirementProfile).where(
                    RequirementProfile.session_id == session_id
                )
            )
            profile = result.scalar_one_or_none()
            if profile is None:
                # Return default profile structure
                return {
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
            return profile.to_dict()

    async def save_profile(self, session_id: str, profile: dict) -> dict:
        """Full overwrite save of a requirement profile."""
        async with await self._get_session() as s:
            result = await s.execute(
                select(RequirementProfile).where(
                    RequirementProfile.session_id == session_id
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                for key in (
                    "project_name",
                    "business_background",
                    "current_process",
                    "user_roles",
                    "business_flow",
                    "functional_requirements",
                    "existing_systems",
                    "non_functional",
                    "data_scale",
                    "constraints",
                    "success_criteria",
                    "covered_topics",
                    "pending_questions",
                    "sufficiency_score",
                ):
                    if key in profile:
                        setattr(existing, key, profile[key])
                existing.updated_at = datetime.now(timezone.utc)
                # Sync profile fields to session row
                session_updates = {"updated_at": datetime.now(timezone.utc)}
                if profile.get("project_name"):
                    session_updates["project_name"] = profile["project_name"]
                score = profile.get("sufficiency_score", 0.0)
                if score:
                    session_updates["sufficiency_score"] = score
                await s.execute(
                    update(Session)
                    .where(Session.id == session_id)
                    .values(**session_updates)
                )
                await s.commit()
                await s.refresh(existing)
                return existing.to_dict()
            else:
                # Create new profile
                row = RequirementProfile(
                    session_id=session_id,
                    **{k: v for k, v in profile.items() if hasattr(RequirementProfile, k) and k != "session_id"},
                )
                s.add(row)
                session_updates = {"updated_at": datetime.now(timezone.utc)}
                if profile.get("project_name"):
                    session_updates["project_name"] = profile["project_name"]
                score = profile.get("sufficiency_score", 0.0)
                if score:
                    session_updates["sufficiency_score"] = score
                await s.execute(
                    update(Session)
                    .where(Session.id == session_id)
                    .values(**session_updates)
                )
                await s.commit()
                await s.refresh(row)
                return row.to_dict()

    async def update_profile_field(
        self, session_id: str, field: str, value: Any
    ) -> dict:
        """Update a single field in the requirement profile.
        Creates the profile row if it doesn't exist yet.
        """
        async with await self._get_session() as s:
            result = await s.execute(
                select(RequirementProfile).where(
                    RequirementProfile.session_id == session_id
                )
            )
            profile = result.scalar_one_or_none()
            if profile is None:
                profile = RequirementProfile(session_id=session_id)
                s.add(profile)
                await s.flush()

            if hasattr(profile, field):
                setattr(profile, field, value)
            profile.updated_at = datetime.now(timezone.utc)
            await s.commit()
            await s.refresh(profile)
            return profile.to_dict()

    # ── PRDs ──

    async def save_prd(
        self,
        session_id: str,
        project_name: str = "",
        mode: str = "one_shot",
        sections: list | None = None,
        markdown: str = "",
        workspace_id: str = "",
    ) -> dict:
        async with await self._get_session() as s:
            # Get next version number
            result = await s.execute(
                select(func.coalesce(func.max(GeneratedPRD.version), 0)).where(
                    GeneratedPRD.session_id == session_id
                )
            )
            max_version = result.scalar() or 0
            next_version = max_version + 1

            prd = GeneratedPRD(
                session_id=session_id,
                workspace_id=workspace_id,
                version=next_version,
                title=project_name,
                mode=mode,
                sections=sections or [],
                markdown=markdown,
            )
            s.add(prd)
            # Mark session as complete
            await s.execute(
                update(Session)
                .where(Session.id == session_id)
                .values(
                    status="complete",
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await s.commit()
            await s.refresh(prd)
            return prd.to_dict()

    async def get_prd(
        self, session_id: str, version: int | None = None
    ) -> dict | None:
        async with await self._get_session() as s:
            if version is not None:
                result = await s.execute(
                    select(GeneratedPRD).where(
                        GeneratedPRD.session_id == session_id,
                        GeneratedPRD.version == version,
                    )
                )
            else:
                result = await s.execute(
                    select(GeneratedPRD)
                    .where(GeneratedPRD.session_id == session_id)
                    .order_by(GeneratedPRD.version.desc())
                    .limit(1)
                )
            prd = result.scalar_one_or_none()
            return prd.to_dict() if prd else None

    async def list_prds(self, session_id: str) -> list[dict]:
        async with await self._get_session() as s:
            result = await s.execute(
                select(GeneratedPRD)
                .where(GeneratedPRD.session_id == session_id)
                .order_by(GeneratedPRD.version.desc())
            )
            prds = result.scalars().all()
            return [p.to_dict() for p in prds]


    # ── Dashboard ──

    async def get_dashboard_overview(self) -> dict:
        async with await self._get_session() as s:
            # Total sessions
            total = await s.scalar(select(func.count(Session.id)))

            # By status
            status_result = await s.execute(
                select(Session.status, func.count(Session.id).label("count"))
                .group_by(Session.status)
            )
            by_status = {row.status: row[1] for row in status_result}

            # Average sufficiency
            avg = await s.scalar(
                select(func.avg(Session.sufficiency_score)).where(
                    Session.sufficiency_score > 0
                )
            )

            # Total PRDs
            total_prds = await s.scalar(select(func.count(GeneratedPRD.id)))

            # Total messages
            total_msgs = await s.scalar(select(func.count(ChatMessage.id)))

            return {
                "total_sessions": total or 0,
                "by_status": by_status,
                "avg_sufficiency": round(float(avg or 0), 2),
                "total_prds": total_prds or 0,
                "total_messages": total_msgs or 0,
            }

    async def get_trend_data(
        self,
        granularity: str = "day",
        days: int = 30,
    ) -> list[dict]:
        from sqlalchemy import func as sa_func

        async with await self._get_session() as s:
            if granularity == "day":
                date_trunc = sa_func.date(Session.created_at)
            elif granularity == "week":
                date_trunc = sa_func.date_trunc("week", Session.created_at)
            elif granularity == "month":
                date_trunc = sa_func.date_trunc("month", Session.created_at)
            else:
                date_trunc = sa_func.date(Session.created_at)

            stmt = (
                select(
                    date_trunc.label("date"),
                    sa_func.count(Session.id).label("sessions"),
                )
                .where(
                    Session.created_at
                    >= func.now() - text(f"INTERVAL {days} DAY")
                )
                .group_by(date_trunc)
                .order_by(date_trunc)
            )
            session_rows = await s.execute(stmt)

            if granularity == "day":
                prd_date_trunc = sa_func.date(GeneratedPRD.created_at)
            elif granularity == "week":
                prd_date_trunc = sa_func.date_trunc("week", GeneratedPRD.created_at)
            elif granularity == "month":
                prd_date_trunc = sa_func.date_trunc("month", GeneratedPRD.created_at)
            else:
                prd_date_trunc = sa_func.date(GeneratedPRD.created_at)

            prd_stmt = (
                select(
                    prd_date_trunc.label("date"),
                    sa_func.count(GeneratedPRD.id).label("prds"),
                )
                .where(
                    GeneratedPRD.created_at
                    >= func.now() - text(f"INTERVAL {days} DAY")
                )
                .group_by(prd_date_trunc)
                .order_by(prd_date_trunc)
            )
            prd_rows = await s.execute(prd_stmt)

            # Merge into time series
            session_map: dict[str, int] = {}
            for row in session_rows:
                d = str(row.date) if row.date else ""
                session_map[d] = row.sessions

            prd_map: dict[str, int] = {}
            for row in prd_rows:
                d = str(row.date) if row.date else ""
                prd_map[d] = row.prds

            all_dates = sorted(set(list(session_map.keys()) + list(prd_map.keys())))
            return [
                {
                    "date": d,
                    "sessions": session_map.get(d, 0),
                    "prds": prd_map.get(d, 0),
                }
                for d in all_dates
            ]

    # ── Audit ──

    async def log_audit(
        self,
        action: str,
        user_id: str = "",
        session_id: str = "",
        detail: dict | None = None,
        ip_address: str = "",
    ) -> None:
        async with await self._get_session() as s:
            log = AuditLog(
                user_id=user_id,
                session_id=session_id,
                action=action,
                detail=detail or {},
                ip_address=ip_address,
            )
            s.add(log)
            await s.commit()

    # ── Health ──

    async def health(self) -> dict:
        return {"backend": "mysql", "status": "ok"}
    # ── Requirement Proposals ──

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
        async with await self._get_session() as s:
            p = RequirementProposal(
                workspace_id=workspace_id,
                source_session_id=source_session_id,
                submitter_id=submitter_id,
                title=title,
                background=background,
                pain_points=pain_points or [],
                desired_outcome=desired_outcome,
                scope_note=scope_note,
                urgency=urgency,
                priority=priority,
                status=status,
                tags=tags or [],
            )
            s.add(p)
            await s.commit()
            await s.refresh(p)
            return p.to_dict()

    async def get_proposal(self, proposal_id: str) -> dict | None:
        async with await self._get_session() as s:
            stmt = select(RequirementProposal).where(
                RequirementProposal.id == proposal_id
            )
            result = await s.execute(stmt)
            row = result.scalar_one_or_none()
            return row.to_dict() if row else None

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
        async with await self._get_session() as s:
            stmt = select(RequirementProposal).where(
                RequirementProposal.workspace_id == workspace_id
            )
            if status:
                stmt = stmt.where(RequirementProposal.status == status)
            if urgency:
                stmt = stmt.where(RequirementProposal.urgency == urgency)
            if priority:
                stmt = stmt.where(RequirementProposal.priority == priority)
            stmt = stmt.order_by(RequirementProposal.created_at.desc())
            stmt = stmt.offset(offset).limit(limit)
            result = await s.execute(stmt)
            rows = result.scalars().all()
            return [r.to_dict() for r in rows]

    async def update_proposal(
        self, proposal_id: str, **kwargs
    ) -> dict | None:
        async with await self._get_session() as s:
            stmt = select(RequirementProposal).where(
                RequirementProposal.id == proposal_id
            )
            result = await s.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return None
            for key, value in kwargs.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            row.updated_at = datetime.now(timezone.utc)
            await s.commit()
            await s.refresh(row)
            return row.to_dict()

    async def delete_proposal(self, proposal_id: str) -> bool:
        async with await self._get_session() as s:
            stmt = select(RequirementProposal).where(
                RequirementProposal.id == proposal_id
            )
            result = await s.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return False
            await s.delete(row)
            await s.commit()
            return True

    async def count_proposals(self, workspace_id: str) -> dict:
        async with await self._get_session() as s:
            stmt = (
                select(
                    RequirementProposal.status,
                    func.count(RequirementProposal.id),
                )
                .where(RequirementProposal.workspace_id == workspace_id)
                .group_by(RequirementProposal.status)
            )
            result = await s.execute(stmt)
            rows = result.all()
            counts: dict[str, int] = {}
            for row in rows:
                key = str(row[0]) if row[0] else "unknown"
                counts[key] = int(row[1])
            return counts

    async def get_prd_by_id(self, prd_id: str) -> dict | None:
        """Get PRD by primary key id."""
        async with await self._get_session() as s:
            result = await s.execute(
                select(GeneratedPRD).where(GeneratedPRD.id == prd_id)
            )
            prd = result.scalar_one_or_none()
            return prd.to_dict() if prd else None

    async def list_prds_by_workspace(self, workspace_id: str) -> list[dict]:
        """List all PRDs in a workspace, ordered by created_at desc."""
        async with await self._get_session() as s:
            result = await s.execute(
                select(GeneratedPRD)
                .where(GeneratedPRD.workspace_id == workspace_id)
                .order_by(GeneratedPRD.created_at.desc())
            )
            prds = result.scalars().all()
            return [p.to_dict() for p in prds]

    async def update_prd(self, prd_id: str, **kwargs) -> dict | None:
        """Update PRD fields. Returns updated PRD or None."""
        async with await self._get_session() as s:
            result = await s.execute(
                select(GeneratedPRD).where(GeneratedPRD.id == prd_id)
            )
            prd = result.scalar_one_or_none()
            if not prd:
                return None
            for key, val in kwargs.items():
                if val is not None and hasattr(prd, key):
                    setattr(prd, key, val)
            await s.commit()
            await s.refresh(prd)
            return prd.to_dict()

