# Third-party packages
import pytest

# App packages
from server import auth
from server.flask import app
from tests.utils import make_fake_bulk_response

WORKSPACE_ID = "58278355-f4f3-56d2-aa81-498250f27798"


class MockEsClient:
    """Minimal ES client stand-in for Flask-level bulk route tests. `bulk()`
    echoes back whatever operations were submitted (see
    tests/utils.make_fake_bulk_response); `delete_by_query()` returns a
    canned response, since the cascade-delete routes (workspaces/scenarios/
    benchmarks) don't vary their response shape with batch size."""

    def __init__(self):
        self.bulk_calls = []
        self.delete_by_query_calls = []

    def bulk(self, **kwargs):
        self.bulk_calls.append(kwargs)
        return make_fake_bulk_response(kwargs.get("operations") or [])

    def delete_by_query(self, **kwargs):
        self.delete_by_query_calls.append(kwargs)
        return {"took": 1, "deleted": 0, "failures": []}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    mock_es_client = MockEsClient()
    monkeypatch.setattr("server.flask.es", lambda _: mock_es_client)
    test_client = app.test_client()
    test_client.mock_es = mock_es_client
    return test_client


def _valid_workspace():
    return {
        "name": "Products", "index_pattern": "products", "params": ["text"],
        "rating_scale": {"min": 0, "max": 4},
    }


####  Workspaces: create (POST /api/workspaces)  ###############################

def test_create_single_object_is_byte_identical_shape(client):
    response = client.post("/api/workspaces", json=_valid_workspace())
    assert response.status_code == 201
    body = response.get_json()
    assert "items" not in body
    assert "status" not in body
    assert body["result"] == "created"


def test_create_single_object_invalid_returns_400(client):
    invalid = _valid_workspace()
    del invalid["name"]
    response = client.post("/api/workspaces", json=invalid)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_array_all_valid_returns_200(client):
    response = client.post("/api/workspaces", json=[_valid_workspace(), _valid_workspace()])
    assert response.status_code == 200
    body = response.get_json()
    assert body["errors"] is False
    assert len(body["items"]) == 2


def test_create_array_mixed_validity_returns_207(client):
    invalid = _valid_workspace()
    del invalid["name"]
    response = client.post("/api/workspaces", json=[_valid_workspace(), invalid])
    assert response.status_code == 207
    body = response.get_json()
    assert body["errors"] is True
    statuses = [next(iter(item.values()))["status"] for item in body["items"]]
    assert statuses == [201, 400]


def test_create_single_bulk_call_per_request(client):
    client.post("/api/workspaces", json=[_valid_workspace(), _valid_workspace(), _valid_workspace()])
    assert len(client.mock_es.bulk_calls) == 1
    assert client.mock_es.bulk_calls[0]["refresh"] is True


####  Workspaces: update (PUT /api/workspaces/<_id> and /api/workspaces)  ######

def test_update_single_item_route_is_byte_identical_shape(client):
    response = client.put("/api/workspaces/ws-1", json={"name": "Renamed"})
    assert response.status_code == 200
    body = response.get_json()
    assert "items" not in body
    assert "status" not in body
    assert body["result"] == "updated"


def test_update_bulk_collection_route_returns_array_envelope(client):
    response = client.put(
        "/api/workspaces",
        json=[{"_id": "ws-1", "name": "A"}, {"_id": "ws-2", "name": "B"}],
    )
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["items"]) == 2
    assert len(client.mock_es.bulk_calls) == 1


####  Workspaces: delete (DELETE /api/workspaces/<_id> and /api/workspaces)  ###

def test_delete_single_item_route_uses_delete_by_query(client):
    response = client.delete("/api/workspaces/ws-1")
    assert response.status_code == 200
    assert len(client.mock_es.delete_by_query_calls) >= 1


def test_delete_bulk_collection_route_widens_to_multiple_ids(client):
    response = client.delete(
        "/api/workspaces",
        json=[{"_id": "ws-1"}, {"_id": "ws-2"}],
    )
    assert response.status_code == 200
    first_call_body = client.mock_es.delete_by_query_calls[0]["body"]
    should = first_call_body["query"]["bool"]["should"]
    assert should[0]["bool"]["filter"][1]["terms"]["_id"] == ["ws-1", "ws-2"]


####  Displays: bulk delete uses `_bulk`, not delete_by_query  #################

def test_displays_delete_single_item_route_is_byte_identical_shape(client):
    response = client.delete(f"/api/workspaces/{WORKSPACE_ID}/displays/d-1")
    assert response.status_code == 200
    body = response.get_json()
    assert "items" not in body
    assert body["result"] == "deleted"


def test_displays_delete_bulk_collection_route_returns_array_envelope(client):
    response = client.delete(
        f"/api/workspaces/{WORKSPACE_ID}/displays",
        json=[{"_id": "d-1"}, {"_id": "d-2"}],
    )
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["items"]) == 2
    assert len(client.mock_es.bulk_calls) == 1


####  Judgements: set (PUT, already a collection-level route)  ################

def test_judgements_set_single_object_is_byte_identical_shape(client):
    response = client.put(
        f"/api/workspaces/{WORKSPACE_ID}/judgements",
        json={"scenario_id": "sc-1", "index": "products", "doc_id": "1", "rating": 3},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "items" not in body
    assert body["result"] == "updated"


def test_judgements_set_array_returns_bulk_envelope(client):
    response = client.put(
        f"/api/workspaces/{WORKSPACE_ID}/judgements",
        json=[
            {"scenario_id": "sc-1", "index": "products", "doc_id": "1", "rating": 3},
            {"scenario_id": "sc-1", "index": "products", "doc_id": "2", "rating": 1},
        ],
    )
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["items"]) == 2
    assert len(client.mock_es.bulk_calls) == 1
    assert client.mock_es.bulk_calls[0]["refresh"] is True
