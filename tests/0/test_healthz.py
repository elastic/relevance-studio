import pytest
import requests

@pytest.mark.dependency(name="test_healthz.test_is_healthy")
def test_is_healthy(services):
    r = requests.get(f"{services['esrs']}/healthz")
    assert r.status_code == 200
    assert r.json() == { "acknowledged": True }

@pytest.mark.dependency(
    name="test_healthz.test_complete",
    depends=["test_healthz.test_is_healthy"],
    scope="session"
)
def test_complete():
    """
    No-op test to group dependencies.
    """
    pass