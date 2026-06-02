import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.pm_agent_service import pm_agent_service


async def fake_sse_events(*args, **kwargs):
    yield {"type": "content", "data": "ok"}
    yield {"type": "sufficiency", "data": {"score": 0.3, "threshold": 0.75}}


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_profile_endpoint(client):
    from app.agent.pm.tools import _profile_store
    _profile_store.clear()
    response = await client.get("/api/pm/profile/api-test")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "api-test"
    assert "profile" in data


@pytest.mark.asyncio
async def test_chat_endpoint_returns_sse(client, monkeypatch):
    monkeypatch.setattr(pm_agent_service, "chat", fake_sse_events)
    response = await client.post("/api/pm/chat", json={
        "message": "我想做一个外卖系统", "session_id": "api-test-1",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_generate_endpoint_returns_sse(client, monkeypatch):
    monkeypatch.setattr(pm_agent_service, "generate_prd", fake_sse_events)
    response = await client.post("/api/pm/generate", json={
        "session_id": "api-test-1", "mode": "one_shot",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_continue_endpoint_returns_sse(client, monkeypatch):
    monkeypatch.setattr(pm_agent_service, "continue_generation", fake_sse_events)
    response = await client.post("/api/pm/continue", json={
        "session_id": "api-test-1",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_agent_endpoint_chat_returns_sse(client, monkeypatch):
    monkeypatch.setattr(pm_agent_service, "handle", fake_sse_events)
    response = await client.post("/api/pm/agent", json={
        "message": "我想做一个外卖系统", "session_id": "api-test-2", "mode": "one_shot",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_agent_endpoint_generate_returns_sse(client, monkeypatch):
    monkeypatch.setattr(pm_agent_service, "handle", fake_sse_events)
    response = await client.post("/api/pm/agent", json={
        "message": "生成PRD", "session_id": "api-test-2", "mode": "one_shot",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_upload_endpoint_rejects_no_file(client):
    response = await client.post("/api/pm/upload")
    assert response.status_code in (422, 400)
