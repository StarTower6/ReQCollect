import pytest

from app.agent.pm.phase2.generator import get_section_generator


@pytest.mark.asyncio
async def test_generator_yields_content():
    section = {
        "key": "project_overview",
        "title": "1. 项目概述",
        "prompt": "Write a brief project overview for a food delivery app.",
    }
    chunks = []
    async for chunk in get_section_generator().generate(section):
        chunks.append(chunk)
    assert len(chunks) > 0
    full = "".join(chunks)
    assert len(full) > 20


@pytest.mark.asyncio
async def test_generator_starts_with_section_heading():
    section = {
        "key": "acceptance",
        "title": "7. 验收标准",
        "prompt": "Write acceptance criteria for a login system.",
    }
    chunks = []
    async for chunk in get_section_generator().generate(section):
        chunks.append(chunk)
    full = "".join(chunks)
    assert "##" in full or len(full) > 30
