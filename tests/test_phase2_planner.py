from app.agent.pm.phase2.planner import prd_planner


def test_planner_creates_all_sections():
    profile = {
        "project_name": "Test",
        "project_type": "Web",
        "industry": "Tech",
        "elevator_pitch": "A test project",
        "user_roles": [],
        "functional_modules": [],
        "non_functional": {},
        "constraints": [],
        "assumptions": [],
    }
    sections = prd_planner.plan(profile)
    assert len(sections) == 8
    assert sections[0]["title"] == "1. 项目概述"
    assert sections[-1]["title"] == "8. 附录"
    assert all(s["status"] == "pending" for s in sections)


def test_planner_one_shot_vs_incremental():
    profile = {"project_name": "Test"}
    sections_os = prd_planner.plan(profile, "one_shot")
    sections_inc = prd_planner.plan(profile, "incremental")
    assert len(sections_os) == len(sections_inc)
