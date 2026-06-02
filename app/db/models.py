"""SQLAlchemy ORM models for PM Agent."""

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProfileStatus(enum.StrEnum):
    MINING = "mining"
    READY = "ready"
    GENERATING = "generating"
    COMPLETE = "complete"


class RequirementProfileModel(Base):
    __tablename__ = "requirement_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_name: Mapped[str] = mapped_column(String(200), default="")
    project_type: Mapped[str] = mapped_column(String(100), default="")
    industry: Mapped[str] = mapped_column(String(100), default="")
    elevator_pitch: Mapped[str] = mapped_column(Text, default="")
    user_roles: Mapped[dict] = mapped_column(JSON, default=list)
    functional_modules: Mapped[dict] = mapped_column(JSON, default=list)
    non_functional: Mapped[dict] = mapped_column(JSON, default=dict)
    constraints: Mapped[dict] = mapped_column(JSON, default=list)
    assumptions: Mapped[dict] = mapped_column(JSON, default=list)
    covered_topics: Mapped[dict] = mapped_column(JSON, default=list)
    pending_questions: Mapped[dict] = mapped_column(JSON, default=list)
    sufficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ProfileStatus] = mapped_column(
        SAEnum(ProfileStatus), default=ProfileStatus.MINING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class GeneratedPRD(Base):
    __tablename__ = "generated_prds"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    mode: Mapped[str] = mapped_column(String(20), default="one_shot")
    sections: Mapped[dict] = mapped_column(JSON, default=list)
    markdown: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(20), default="assistant")
    content: Mapped[str] = mapped_column(Text, default="")
    event_type: Mapped[str] = mapped_column(String(50), default="message")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
