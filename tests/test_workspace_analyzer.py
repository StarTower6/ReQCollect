"""Tests for workspace_analyzer — LLM-based file analyzer."""
import pytest
import tempfile
from app.core.workspace_analyzer import _parse_llm_json
from app.core.workspace_files import WorkspaceFileManager

TEST_WS_ID = "test_ws_analyze"


@pytest.fixture
def fm():
    from app.config import config
    config.data_dir = tempfile.mkdtemp()
    fm = WorkspaceFileManager(TEST_WS_ID)
    # Upload a simple .md file
    content = "# 报销审批系统\n\n员工提交报销单，部门经理审批，财务复核，总经理审批。".encode("utf-8")
    fm.upload_file("报销审批.md", content, "test")
    return fm


def test_parse_llm_json_with_codeblock():
    """_parse_llm_json handles ```json ... ``` wrapped output."""
    raw = '```json\n{"summary": "test", "tags": ["a"], "domain": "d"}\n```'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result["summary"] == "test"


def test_parse_llm_json_plain():
    """_parse_llm_json handles plain JSON without wrapping."""
    raw = '{"summary": "test", "tags": ["a"], "domain": "d"}'
    result = _parse_llm_json(raw)
    assert result is not None


def test_parse_llm_json_invalid():
    """_parse_llm_json returns None on garbage input."""
    assert _parse_llm_json("not json at all") is None
    assert _parse_llm_json("") is None


def test_upsert_analysis(fm):
    """upsert_analysis writes analysis field without changing other fields."""
    analysis = {"summary": "报销系统", "tags": ["报销"], "domain": "审批"}
    fm.upsert_analysis("报销审批.md", analysis)
    info = fm.get_file_info("报销审批.md")
    assert info is not None
    assert info["analysis"] == analysis
