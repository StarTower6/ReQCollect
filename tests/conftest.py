import pytest
from httpx import ASGITransport, AsyncClient

from app.agent.pm.tools import _profile_store
from app.db.compat import FileDataStore
from app.db import DataStore
from app.main import app as _app


@pytest.fixture(autouse=True)
def clear_profile_store():
    _profile_store.clear()
    yield
    _profile_store.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_datastore() -> DataStore:
    """Create a clean FileDataStore with a temp directory for tests."""
    import tempfile, os
    old = os.environ.get("DATA_DIR")
    tmpdir = tempfile.mkdtemp(prefix="reqcollect_test_")
    os.environ["DATA_DIR"] = tmpdir
    ds = FileDataStore()
    yield ds
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    if old:
        os.environ["DATA_DIR"] = old
    else:
        os.environ.pop("DATA_DIR", None)

