import pytest
import requests

@pytest.fixture(scope="module")
def esrs_response(services, wipe_data):
    """
    Setup esrs-* index templates.
    """
    response = requests.get(f"{services['esrs']}/")
    assert response.status_code == 200  # fail early if broken
    return response.text

@pytest.mark.dependency(
    depends=["test_healthz.test_complete"],
    scope="session"
)
def test_has_correct_contents(esrs_response):
    assert esrs_response.startswith('<!doctype html><html lang="en"><head><title>Elasticsearch Relevance Studio</title>')