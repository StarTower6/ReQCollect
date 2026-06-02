from app.agent.pm.state import RequirementProfile


def test_requirement_profile_defaults():
    profile: RequirementProfile = {
        "project_name": "",
        "project_type": "",
        "industry": "",
        "elevator_pitch": "",
        "user_roles": [],
        "functional_modules": [],
        "non_functional": {},
        "constraints": [],
        "assumptions": [],
        "covered_topics": [],
        "pending_questions": [],
        "sufficiency_score": 0.0,
    }
    assert profile["project_name"] == ""
    assert profile["sufficiency_score"] == 0.0
    assert len(profile["user_roles"]) == 0


def test_requirement_profile_partial():
    profile: RequirementProfile = {
        "project_name": "Test Project",
        "project_type": "Web App",
        "industry": "Finance",
    }
    assert profile["project_name"] == "Test Project"
    assert profile.get("elevator_pitch", "") == ""
