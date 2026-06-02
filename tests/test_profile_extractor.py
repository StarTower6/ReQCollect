from app.agent.pm.phase1.profile_extractor import apply_profile_hints
from app.agent.pm.phase1.sufficiency import evaluate_profile_sufficiency
from app.agent.pm.tools import get_profile, hydrate_profile


def test_profile_hints_raise_sufficiency_from_user_message():
    thread_id = "hint-test"
    changed = apply_profile_hints(
        thread_id,
        (
            "我想做一个餐厅外卖智能客服系统，项目类型是SaaS，行业是餐饮外卖，"
            "核心痛点是客服响应慢。主要用户有餐厅老板、店员、客服主管，"
            "核心功能包括订单问答、退款咨询、差评预警、人工转接。"
        ),
    )

    assert "project_name" in changed
    assert "project_type" in changed
    assert "functional_modules" in changed

    result = evaluate_profile_sufficiency(thread_id)
    assert result.score > 0.0


def test_hydrate_profile_keeps_existing_non_empty_values():
    thread_id = "hydrate-test"
    profile = get_profile(thread_id)
    profile["project_name"] = "当前项目"
    profile["sufficiency_score"] = 0.4

    hydrate_profile(thread_id, {
        "project_name": "",
        "sufficiency_score": 0.1,
        "industry": "餐饮",
    })

    assert profile["project_name"] == "当前项目"
    assert profile["sufficiency_score"] == 0.4
    assert profile["industry"] == "餐饮"
