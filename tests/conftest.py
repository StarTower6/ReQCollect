import pytest

from app.agent.pm.tools import _profile_store


@pytest.fixture(autouse=True)
def clear_profile_store():
    _profile_store.clear()
    yield
    _profile_store.clear()
