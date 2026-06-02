import json

from app.agent.pm.tools import (
    get_profile,
    get_profile_summary,
    update_requirement_profile,
)


def test_get_profile_creates_default():
    profile = get_profile("test-thread")
    assert profile["project_name"] == ""
    assert profile["sufficiency_score"] == 0.0


def test_update_profile_string_field():
    update_requirement_profile.invoke({
        "field": "project_name",
        "value": "报销审批系统",
        "thread_id": "test-thread",
    })
    profile = get_profile("test-thread")
    assert profile["project_name"] == "报销审批系统"


def test_update_profile_list_field():
    roles = json.dumps([
        {"role": "员工", "desc": "提交报销申请"},
        {"role": "经理", "desc": "审批报销"},
    ])
    update_requirement_profile.invoke({
        "field": "user_roles",
        "value": roles,
        "thread_id": "test-thread",
    })
    profile = get_profile("test-thread")
    assert len(profile["user_roles"]) == 2
    assert profile["user_roles"][0]["role"] == "员工"


def test_get_profile_summary():
    update_requirement_profile.invoke({
        "field": "project_name",
        "value": "测试项目",
        "thread_id": "summary-test",
    })
    summary = get_profile_summary.invoke({"thread_id": "summary-test"})
    assert "测试项目" in summary
    assert "Not Yet Covered" in summary
