"""Data access layer for requirement profiles and PRDs."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatMessageModel, GeneratedPRD, RequirementProfileModel


class ProfileRepository:

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        session_id: str,
    ) -> RequirementProfileModel:
        result = await session.execute(
            select(RequirementProfileModel).where(
                RequirementProfileModel.session_id == session_id
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = RequirementProfileModel(
                id=str(uuid.uuid4()),
                session_id=session_id,
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
        return profile

    @staticmethod
    async def update_field(
        session: AsyncSession,
        session_id: str,
        field: str,
        value,
    ) -> RequirementProfileModel:
        profile = await ProfileRepository.get_or_create(session, session_id)
        if hasattr(profile, field):
            setattr(profile, field, value)
            await session.commit()
            await session.refresh(profile)
        return profile

    @staticmethod
    async def update_from_dict(
        session: AsyncSession,
        session_id: str,
        data: dict,
    ) -> RequirementProfileModel:
        profile = await ProfileRepository.get_or_create(session, session_id)
        for key, value in data.items():
            if hasattr(profile, key) and key != "id":
                setattr(profile, key, value)
        await session.commit()
        await session.refresh(profile)
        return profile

    @staticmethod
    async def get_by_session(
        session: AsyncSession,
        session_id: str,
    ) -> dict | None:
        profile = await ProfileRepository.get_or_create(session, session_id)
        return {
            "project_name": profile.project_name,
            "project_type": profile.project_type,
            "industry": profile.industry,
            "elevator_pitch": profile.elevator_pitch,
            "user_roles": profile.user_roles,
            "functional_modules": profile.functional_modules,
            "non_functional": profile.non_functional,
            "constraints": profile.constraints,
            "assumptions": profile.assumptions,
            "covered_topics": profile.covered_topics,
            "pending_questions": profile.pending_questions,
            "sufficiency_score": profile.sufficiency_score,
        }


class SessionRepository:

    @staticmethod
    async def list_sessions(session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(RequirementProfileModel).order_by(
                RequirementProfileModel.updated_at.desc()
            ).limit(50)
        )
        return [
            {
                "session_id": p.session_id,
                "project_name": p.project_name or "未命名项目",
                "status": p.status.value if p.status else "mining",
                "sufficiency_score": p.sufficiency_score,
                "updated_at": p.updated_at.isoformat() if p.updated_at else "",
            }
            for p in result.scalars().all()
        ]


class PRDRepository:

    @staticmethod
    async def save(
        session: AsyncSession,
        session_id: str,
        title: str,
        mode: str,
        sections: list,
        markdown: str,
    ) -> GeneratedPRD:
        prd = GeneratedPRD(
            id=str(uuid.uuid4()),
            session_id=session_id,
            title=title,
            mode=mode,
            sections=sections,
            markdown=markdown,
        )
        session.add(prd)
        await session.commit()
        await session.refresh(prd)
        return prd

    @staticmethod
    async def list_by_session(
        session: AsyncSession,
        session_id: str,
    ) -> list[GeneratedPRD]:
        result = await session.execute(
            select(GeneratedPRD)
            .where(GeneratedPRD.session_id == session_id)
            .order_by(GeneratedPRD.created_at.desc())
        )
        return list(result.scalars().all())


class ChatHistoryRepository:

    @staticmethod
    async def add_message(
        session: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        event_type: str = "message",
        meta: dict | None = None,
    ) -> ChatMessageModel:
        profile = await ProfileRepository.get_or_create(session, session_id)
        profile.updated_at = datetime.utcnow()
        message = ChatMessageModel(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            event_type=event_type,
            meta=meta or {},
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message

    @staticmethod
    async def list_by_session(
        session: AsyncSession,
        session_id: str,
        limit: int = 200,
    ) -> list[dict]:
        result = await session.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
            .limit(limit)
        )
        return [
            {
                "id": message.id,
                "session_id": message.session_id,
                "role": message.role,
                "content": message.content,
                "event_type": message.event_type,
                "meta": message.meta or {},
                "created_at": message.created_at.isoformat() if message.created_at else "",
            }
            for message in result.scalars().all()
        ]
