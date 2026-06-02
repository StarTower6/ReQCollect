import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.repository import (
    ChatHistoryRepository,
    PRDRepository,
    ProfileRepository,
    SessionRepository,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_creates_new_profile(session):
    profile = await ProfileRepository.get_or_create(session, "new-session")
    assert profile is not None
    assert profile.session_id == "new-session"
    assert profile.project_name == ""


@pytest.mark.asyncio
async def test_get_or_create_returns_existing(session):
    p1 = await ProfileRepository.get_or_create(session, "same-session")
    p2 = await ProfileRepository.get_or_create(session, "same-session")
    assert p1.id == p2.id


@pytest.mark.asyncio
async def test_update_field(session):
    profile = await ProfileRepository.update_field(
        session, "test-session", "project_name", "HR系统"
    )
    assert profile.project_name == "HR系统"


@pytest.mark.asyncio
async def test_update_from_dict(session):
    profile = await ProfileRepository.update_from_dict(session, "test-session-2", {
        "project_name": "报销系统",
        "industry": "金融",
        "sufficiency_score": 0.8,
    })
    assert profile.project_name == "报销系统"
    assert profile.industry == "金融"
    assert profile.sufficiency_score == 0.8


@pytest.mark.asyncio
async def test_prd_save_and_list(session):
    prd = await PRDRepository.save(
        session,
        session_id="test-prd-session",
        title="HR系统 PRD",
        mode="one_shot",
        sections=[{"key": "overview", "title": "概述", "status": "done"}],
        markdown="# HR系统 PRD\n\n## 概述\n...",
    )
    assert prd.id is not None
    assert prd.title == "HR系统 PRD"

    prds = await PRDRepository.list_by_session(session, "test-prd-session")
    assert len(prds) == 1
    assert prds[0].title == "HR系统 PRD"


@pytest.mark.asyncio
async def test_chat_history_save_and_list(session):
    await ChatHistoryRepository.add_message(
        session,
        session_id="history-session",
        role="user",
        content="我想做一个报销系统",
    )
    await ChatHistoryRepository.add_message(
        session,
        session_id="history-session",
        role="assistant",
        content="先确认用户角色和审批流程。",
    )

    messages = await ChatHistoryRepository.list_by_session(session, "history-session")

    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "我想做一个报销系统"
    assert messages[1]["content"] == "先确认用户角色和审批流程。"


@pytest.mark.asyncio
async def test_message_save_creates_recent_session(session):
    await ChatHistoryRepository.add_message(
        session,
        session_id="recent-session",
        role="user",
        content="新需求",
    )

    sessions = await SessionRepository.list_sessions(session)

    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "recent-session"
    assert sessions[0]["project_name"] == "未命名项目"
    assert sessions[0]["is_pinned"] is False


@pytest.mark.asyncio
async def test_pin_session_orders_before_recent_unpinned(session):
    await ChatHistoryRepository.add_message(
        session,
        session_id="old-session",
        role="user",
        content="旧会话",
    )
    await ChatHistoryRepository.add_message(
        session,
        session_id="new-session",
        role="user",
        content="新会话",
    )

    updated = await SessionRepository.set_pinned(session, "old-session", True)
    sessions = await SessionRepository.list_sessions(session)

    assert updated is not None
    assert updated["is_pinned"] is True
    assert sessions[0]["session_id"] == "old-session"
    assert sessions[0]["is_pinned"] is True


@pytest.mark.asyncio
async def test_delete_session_removes_profile_history_and_prds(session):
    await ChatHistoryRepository.add_message(
        session,
        session_id="delete-session",
        role="user",
        content="要删除的会话",
    )
    await PRDRepository.save(
        session,
        session_id="delete-session",
        title="删除测试 PRD",
        mode="one_shot",
        sections=[],
        markdown="# 删除测试",
    )

    deleted = await SessionRepository.delete_session(session, "delete-session")

    assert deleted is True
    assert await ChatHistoryRepository.list_by_session(session, "delete-session") == []
    assert await PRDRepository.list_by_session(session, "delete-session") == []
    assert await SessionRepository.delete_session(session, "delete-session") is False
