import pytest
import requests

@pytest.fixture(scope="module")
def api_setup_response(services, wipe_data):
    """
    Setup esrs-* index templates.
    """
    r = requests.post(f"{services['esrs']}/api/setup")
    assert r.status_code == 200  # fail early if broken
    return r.json()
    
def test_api_setup__has_correct_contents(api_setup_response, constants):
    assert sorted(api_setup_response.keys()) == [ "failures", "requests" ]
    assert api_setup_response["response"]["failures"] == 0
    for req in api_setup_response["response"]["requests"]:
        assert sorted(req.keys()) == [ "index_template", "response" ]
        assert sorted(req["response"].keys()) == [ "body", "status" ]
        assert req["index_template"] in constants["index_templates"]
        assert req["response"]["body"] == { "acknowledged": True }
        assert req["response"]["status"] == 200
        
def test_api_setup__created_index_templates(services, constants):
    for name in constants["index_templates"]:
        assert services["es"].indices.exists_index_template(name=name)