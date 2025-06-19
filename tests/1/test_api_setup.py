import pytest
import requests

@pytest.fixture(scope="module")
def esrs_response(services, wipe_data):
    """
    Setup esrs-* index templates.
    """
    response = requests.post(f"{services['esrs']}/api/setup")
    assert response.status_code == 200  # fail early if broken
    return response.json()
    
@pytest.mark.dependency(
    name="test_api_setup.test_has_correct_contents",
    depends=["test_healthz.test_complete"],
    scope="session"
)
def test_has_correct_contents(esrs_response, constants):
    assert sorted(esrs_response.keys()) == [ "failures", "requests" ]
    assert esrs_response["failures"] == 0
    for req in esrs_response["requests"]:
        assert sorted(req.keys()) == [ "index_template", "response" ]
        assert sorted(req["response"].keys()) == [ "body", "status" ]
        assert req["index_template"] in constants["index_templates"]
        assert req["response"]["body"] == { "acknowledged": True }
        assert req["response"]["status"] == 200
        
@pytest.mark.dependency(
    name="test_api_setup.test_created_index_templates",
    depends=["test_healthz.test_complete"],
    scope="session"
)
def test_created_index_templates(services, constants):
    for name in constants["index_templates"]:
        assert services["es"].indices.exists_index_template(name=name)
        
@pytest.mark.dependency(
    name="test_api_setup.test_complete",
    depends=[
        "test_api_setup.test_has_correct_contents",
        "test_api_setup.test_created_index_templates"
    ],
    scope="session"
)
def test_complete():
    """
    No-op test to group dependencies.
    """
    pass
