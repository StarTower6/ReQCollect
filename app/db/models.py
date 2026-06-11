"""SQLAlchemy ORM models for ReQCollect.

Six tables mirroring the MySQL schema in docs/requirements/04-存储与数据/README.md:
users, sessions, requirement_profiles, chat_messages, generated_prds, audit_logs.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _new_id() -> str:
    """Generate a UUID-based primary key."""
    return uuid.uuid4().hex[:16]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── User ──


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), default="")
    email: Mapped[str | None] = mapped_column(String(200), default="")
    department: Mapped[str | None] = mapped_column(String(100), default="")
    role: Mapped[str] = mapped_column(
        Enum("admin", "analyst", "reviewer", "business", name="user_role"),
        default="business",
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(String(256), default="")
    source: Mapped[str] = mapped_column(
        Enum("ldap", "wecom", "local", name="user_source"),
        default="local",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        Index("idx_department", "department"),
        Index("idx_role", "role"),
    )

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )


# ── Session ──


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    workspace_id: Mapped[str | None] = mapped_column(String(64), default="")
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(
        Enum("mining", "generating", "complete", name="session_status"),
        default="mining",
    )
    sufficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[dict | None] = mapped_column(JSON, default=list)  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        Index("idx_user", "user_id"),
        Index("idx_status", "status"),
        Index("idx_updated", "updated_at"),
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    profile: Mapped["RequirementProfile | None"] = relationship(
        "RequirementProfile", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    prds: Mapped[list["GeneratedPRD"]] = relationship(
        "GeneratedPRD", back_populates="session", cascade="all, delete-orphan",
        order_by="GeneratedPRD.version",
    )

    def to_dict(self) -> dict:
        return {
            "session_id": self.id,
            "workspace_id": self.workspace_id or "",
            "user_id": self.user_id,
            "project_name": self.project_name or "未命名项目",
            "status": self.status,
            "sufficiency_score": self.sufficiency_score,
            "is_pinned": self.is_pinned,
            "tags": self.tags if isinstance(self.tags, list) else [],
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


# ── Requirement Profile ──


class RequirementProfile(Base):
    __tablename__ = "requirement_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    project_name: Mapped[str] = mapped_column(String(200), default="")
    business_background: Mapped[str | None] = mapped_column(Text, default="")
    current_process: Mapped[str | None] = mapped_column(Text, default="")
    user_roles: Mapped[dict | None] = mapped_column(JSON, default=list)
    business_flow: Mapped[str | None] = mapped_column(Text, default="")
    functional_requirements: Mapped[dict | None] = mapped_column(JSON, default=list)
    existing_systems: Mapped[dict | None] = mapped_column(JSON, default=list)
    non_functional: Mapped[dict | None] = mapped_column(JSON, default=dict)
    data_scale: Mapped[str | None] = mapped_column(String(500), default="")
    constraints: Mapped[dict | None] = mapped_column(JSON, default=list)
    success_criteria: Mapped[dict | None] = mapped_column(JSON, default=list)
    covered_topics: Mapped[dict | None] = mapped_column(JSON, default=list)
    pending_questions: Mapped[dict | None] = mapped_column(JSON, default=list)
    sufficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="profile")

    def to_dict(self) -> dict:
        """Convert to the same dict format used by tools.py get_profile()."""
        return {
            "project_name": self.project_name or "",
            "business_background": self.business_background or "",
            "current_process": self.current_process or "",
            "user_roles": self.user_roles if isinstance(self.user_roles, list) else [],
            "business_flow": self.business_flow or "",
            "functional_requirements": (
                self.functional_requirements
                if isinstance(self.functional_requirements, list)
                else []
            ),
            "existing_systems": (
                self.existing_systems if isinstance(self.existing_systems, list) else []
            ),
            "non_functional": (
                self.non_functional if isinstance(self.non_functional, dict) else {}
            ),
            "data_scale": self.data_scale or "",
            "constraints": self.constraints if isinstance(self.constraints, list) else [],
            "success_criteria": (
                self.success_criteria if isinstance(self.success_criteria, list) else []
            ),
            "covered_topics": (
                self.covered_topics if isinstance(self.covered_topics, list) else []
            ),
            "pending_questions": (
                self.pending_questions if isinstance(self.pending_questions, list) else []
            ),
            "sufficiency_score": self.sufficiency_score or 0.0,
        }


# ── Chat Message ──


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", "event", name="message_role"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), default="message")
    meta: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("idx_session", "session_id"),
        Index("idx_created", "created_at"),
    )

    session: Mapped["Session"] = relationship("Session", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "event_type": self.event_type,
            "meta": self.meta or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


# ── Generated PRD ──


class GeneratedPRD(Base):
    __tablename__ = "generated_prds"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(500), default="")
    mode: Mapped[str] = mapped_column(String(20), default="one_shot")
    sections: Mapped[dict | None] = mapped_column(JSON, default=list)
    markdown: Mapped[str | None] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("idx_session", "session_id"),
        Index("idx_version", "session_id", "version"),
    )

    session: Mapped["Session"] = relationship("Session", back_populates="prds")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "version": self.version,
            "title": self.title or "",
            "mode": self.mode,
            "sections": self.sections if isinstance(self.sections, list) else [],
            "markdown": self.markdown or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


# ── Workspace ──


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), default="")
    description: Mapped[str | None] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


# ── Wiki Page ──


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_wiki_workspace", "workspace_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "title": self.title or "",
            "content": self.content or "",
            "created_by": self.created_by,
            "updated_by": self.updated_by or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


# ── Wiki Link ──


class WikiLink(Base):
    """Stores [[link]] relationships between wiki pages AND workspace files.

    source_ref + source_type -> target_ref + target_type (directed edge).
    source_type / target_type: "wiki" | "file"
    link_type describes the relationship: "reference", "dependency", etc.
    workspace_id ties the link to a workspace for graph queries.
    """

    __tablename__ = "wiki_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    source_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(16), default="wiki")
    target_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(16), default="wiki")
    link_type: Mapped[str] = mapped_column(String(50), default="reference")
    workspace_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("idx_wikilink_source", "source_ref"),
        Index("idx_wikilink_target", "target_ref"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_ref": self.source_ref,
            "source_type": self.source_type,
            "target_ref": self.target_ref,
            "target_type": self.target_type,
            "link_type": self.link_type,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


# ── Audit Log ──


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(64), default="")
    session_id: Mapped[str | None] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("idx_user", "user_id"),
        Index("idx_action", "action"),
        Index("idx_created", "created_at"),
    )
