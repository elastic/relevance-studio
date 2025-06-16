import pytest
import requests

@pytest.fixture(scope="module")
def esrs_response(services, wipe_data):
    """
    Setup esrs-* index templates.
    """
    response = requests.post(f"{services['esrs']}/setup")
    assert response.status_code == 200  # fail early if broken
    return response.json()
    
def test_has_correct_contents(esrs_response, constants):
    assert sorted(esrs_response.keys()) == [ "failures", "requests" ]
    assert esrs_response["failures"] == 0
    for req in esrs_response["requests"]:
        assert sorted(req.keys()) == [ "index_template", "response" ]
        assert sorted(req["response"].keys()) == [ "body", "status" ]
        assert req["index_template"] in constants["index_templates"]
        assert req["response"]["body"] == { "acknowledged": True }
        assert req["response"]["status"] == 200

def test_created_index_templates(services, constants):
    for name in constants["index_templates"]:
        assert services["es"].indices.exists_template(name=name)