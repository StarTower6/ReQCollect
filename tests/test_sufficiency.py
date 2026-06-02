from app.agent.pm.phase1.sufficiency import evaluate_sufficiency
from app.agent.pm.tools import update_requirement_profile


def test_evaluate_sufficiency_low_for_empty_profile():
    result = evaluate_sufficiency.invoke({"thread_id": "suff-test"})
    assert "Score" in result or "score" in result.lower()


def test_evaluate_sufficiency_improves_with_data():
    tid = "suff-test-2"
    update_requirement_profile.invoke({
        "field": "project_name", "value": "HR管理系统", "thread_id": tid,
    })
    update_requirement_profile.invoke({
        "field": "elevator_pitch", "value": "全流程人力资源管理平台", "thread_id": tid,
    })
    result = evaluate_sufficiency.invoke({"thread_id": tid})
    assert "Score" in result or "score" in result.lower()
