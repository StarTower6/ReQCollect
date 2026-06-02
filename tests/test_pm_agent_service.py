from unittest.mock import patch

import pytest

from app.services.pm_agent_service import pm_agent_service


@pytest.mark.asyncio
async def test_get_profile_returns_default():
    from app.agent.pm.tools import _profile_store
    _profile_store.clear()
    profile = await pm_agent_service.get_profile("test-thread")
    assert profile["project_name"] == ""
    assert profile["sufficiency_score"] == 0.0


@pytest.mark.asyncio
async def test_chat_yields_events():
    from app.agent.pm.tools import _profile_store
    _profile_store.clear()

    async def fake_chat(*args, **kwargs):
        yield {"type": "content", "data": "你好！"}
        yield {"type": "sufficiency", "data": {"score": 0.3, "threshold": 0.75}}

    with patch.object(pm_agent_service, 'chat', autospec=True) as mock_chat:
        mock_chat.return_value = fake_chat()
        events = []
        async for event in pm_agent_service.chat("我想做一个系统", "test-thread"):
            events.append(event)
        assert len(events) >= 2
        assert events[0]["type"] == "content"
