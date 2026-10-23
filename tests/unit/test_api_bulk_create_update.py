# Standard packages
import copy

# Third-party packages
import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import BadRequest

# App packages
from server import utils
from server.api import benchmarks, displays, scenarios, strategies, workspaces
from tests.utils import make_fake_bulk_response

WS_ID = "58278355-f4f3-56d2-aa81-498250f27798"

# Each asset's fixtures mirror the valid/minimal inputs used by the
# corresponding tests/unit/test_models_*.py files, plus a deliberately
# invalid variant (missing a required field, or an otherwise-invalid value)
# used to exercise per-item validation failures within a batch.
ASSET_FIXTURES = {
    "workspaces": {
        "module": workspaces,
        "index_name": "esrs-workspaces",
        "supports_custom_id": True,
        "valid_create": {
            "name": "Products", "index_pattern": "products", "params": ["text"],
            "rating_scale": {"min": 0, "max": 4},
        },
        "invalid_create": {
            "index_pattern": "products", "params": ["text"],
            "rating_scale": {"min": 0, "max": 4},
        },  # missing required "name"
        "valid_update": {"name": "Updated Name"},
        "invalid_update": {"params": []},  # fails "must be a non-empty list"
    },
    "displays": {
        "module": displays,
        "index_name": "esrs-displays",
        "supports_custom_id": True,
        "valid_create": {
            "workspace_id": WS_ID, "index_pattern": "products",
            "template": {"body": "{{name.text}}"},
        },
        "invalid_create": {"index_pattern": "products"},  # missing required "workspace_id"
        "valid_update": {"workspace_id": WS_ID, "index_pattern": "products"},
        "invalid_update": {"workspace_id": WS_ID, "index_pattern": ""},  # fails non-empty check
    },
    "scenarios": {
        "module": scenarios,
        "index_name": "esrs-scenarios",
        "supports_custom_id": False,
        "valid_create": {
            "workspace_id": WS_ID, "name": "brown oxfords",
            "values": {"text": "brown oxfords"},
        },
        "invalid_create": {"workspace_id": WS_ID, "values": {"text": "brown oxfords"}},  # missing "name"
        "valid_update": {"workspace_id": WS_ID, "name": "Updated"},
        "invalid_update": {"workspace_id": WS_ID, "name": ""},  # fails non-empty check
    },
    "strategies": {
        "module": strategies,
        "index_name": "esrs-strategies",
        "supports_custom_id": True,
        "valid_create": {"workspace_id": WS_ID, "name": "Classical"},
        "invalid_create": {"name": "Classical"},  # missing required "workspace_id"
        "valid_update": {"workspace_id": WS_ID, "name": "Updated"},
        "invalid_update": {"workspace_id": WS_ID, "name": ""},  # fails non-empty check
    },
    "benchmarks": {
        "module": benchmarks,
        "index_name": "esrs-benchmark-configs",
        "supports_custom_id": True,
        "valid_create": {"workspace_id": WS_ID, "name": "Product Search"},
        "invalid_create": {"name": "Product Search"},  # missing required "workspace_id"
        "valid_update": {"workspace_id": WS_ID, "name": "Updated"},
        "invalid_update": {"workspace_id": WS_ID, "name": ""},  # fails non-empty check
    },
}


def _patch_bulk(monkeypatch, module):
    """Patch `module.es` so `client.bulk()` echoes back whatever operations
    were actually submitted (including randomly-generated `_id`s)."""
    mock_client = MagicMock()
    mock_client.bulk.side_effect = lambda **kwargs: make_fake_bulk_response(kwargs.get("operations") or [])
    monkeypatch.setattr(module, "es", lambda _: mock_client)
    return mock_client


####  Bulk create  ##############################################################

@pytest.mark.parametrize("key", ASSET_FIXTURES.keys())
def test_bulk_create_mixed_validity_batch_reports_per_item_results(monkeypatch, key):
    fx = ASSET_FIXTURES[key]
    mock_client = _patch_bulk(monkeypatch, fx["module"])

    docs = [copy.deepcopy(fx["valid_create"]), copy.deepcopy(fx["invalid_create"])]
    result = fx["module"].create(docs, user="test-user", via="api")

    assert result["errors"] is True
    assert len(result["items"]) == 2
    statuses = [next(iter(item.values()))["status"] for item in result["items"]]
    assert statuses[0] == 201
    assert statuses[1] == 400
    assert "error" in next(iter(result["items"][1].values()))

    # The invalid item never reached Elasticsearch; the valid one did, in a
    # single `_bulk` call with a single refresh for the whole batch.
    assert mock_client.bulk.call_count == 1
    assert mock_client.bulk.call_args.kwargs["refresh"] is True


@pytest.mark.parametrize("key", ASSET_FIXTURES.keys())
def test_bulk_create_all_valid_items_single_bulk_call(monkeypatch, key):
    fx = ASSET_FIXTURES[key]
    mock_client = _patch_bulk(monkeypatch, fx["module"])

    docs = [copy.deepcopy(fx["valid_create"]) for _ in range(3)]
    result = fx["module"].create(docs, user="test-user", via="api")

    assert result["errors"] is False
    assert len(result["items"]) == 3
    assert mock_client.bulk.call_count == 1
    assert mock_client.bulk.call_args.kwargs["refresh"] is True


@pytest.mark.parametrize("key", [k for k, fx in ASSET_FIXTURES.items() if fx["supports_custom_id"]])
def test_bulk_create_respects_custom_id(monkeypatch, key):
    fx = ASSET_FIXTURES[key]
    mock_client = _patch_bulk(monkeypatch, fx["module"])

    doc = copy.deepcopy(fx["valid_create"])
    doc["_id"] = "my-custom-id"
    result = fx["module"].create([doc], user="test-user", via="api")

    item = next(iter(result["items"][0].values()))
    assert item["_id"] == "my-custom-id"


def test_scenarios_create_never_accepts_custom_id(monkeypatch):
    """Scenarios always derive `_id` from (workspace_id, values); passing a
    caller-supplied `_id` is rejected per-item as an unknown field, not
    silently accepted or used."""
    fx = ASSET_FIXTURES["scenarios"]
    mock_client = _patch_bulk(monkeypatch, fx["module"])

    doc = copy.deepcopy(fx["valid_create"])
    doc["_id"] = "should-be-rejected"
    result = fx["module"].create([doc], user="test-user", via="api")

    item = next(iter(result["items"][0].values()))
    assert item["status"] == 400


def test_bulk_create_exceeds_max_batch_size_raises_bad_request(monkeypatch):
    fx = ASSET_FIXTURES["workspaces"]
    _patch_bulk(monkeypatch, fx["module"])
    docs = [copy.deepcopy(fx["valid_create"]) for _ in range(utils.MAX_BULK_BATCH_SIZE + 1)]
    with pytest.raises(BadRequest):
        fx["module"].create(docs, user="test-user", via="api")


####  Bulk update  ###############################################################

@pytest.mark.parametrize("key", ASSET_FIXTURES.keys())
def test_bulk_update_mixed_validity_batch_reports_per_item_results(monkeypatch, key):
    fx = ASSET_FIXTURES[key]
    mock_client = _patch_bulk(monkeypatch, fx["module"])

    valid = copy.deepcopy(fx["valid_update"])
    valid["_id"] = "id-valid"
    invalid = copy.deepcopy(fx["invalid_update"])
    invalid["_id"] = "id-invalid"

    result = fx["module"].update([valid, invalid], user="test-user", via="api")

    assert result["errors"] is True
    statuses = [next(iter(item.values()))["status"] for item in result["items"]]
    assert statuses[0] == 200
    assert statuses[1] == 400

    assert mock_client.bulk.call_count == 1
    assert mock_client.bulk.call_args.kwargs["refresh"] is True

    # Only the valid item's operations reached Elasticsearch.
    operations = mock_client.bulk.call_args.kwargs["operations"]
    assert len(operations) == 2  # one action + one source line
    assert operations[0]["update"]["_id"] == "id-valid"


def test_bulk_update_exceeds_max_batch_size_raises_bad_request(monkeypatch):
    fx = ASSET_FIXTURES["workspaces"]
    _patch_bulk(monkeypatch, fx["module"])
    docs = []
    for i in range(utils.MAX_BULK_BATCH_SIZE + 1):
        doc = copy.deepcopy(fx["valid_update"])
        doc["_id"] = f"id-{i}"
        docs.append(doc)
    with pytest.raises(BadRequest):
        fx["module"].update(docs, user="test-user", via="api")
