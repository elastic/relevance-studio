# Third-party packages
import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import BadRequest

# App packages
from server import utils
from server.api import judgements
from tests.utils import make_fake_bulk_response

WORKSPACE_ID = "58278355-f4f3-56d2-aa81-498250f27798"


def _patch_bulk(monkeypatch):
    mock_client = MagicMock()
    mock_client.bulk.side_effect = lambda **kwargs: make_fake_bulk_response(kwargs.get("operations") or [])
    monkeypatch.setattr(judgements, "es", lambda _: mock_client)
    return mock_client


def test_set_single_bulk_call_with_one_refresh(monkeypatch):
    mock_client = _patch_bulk(monkeypatch)
    items = [
        {"scenario_id": "sc-1", "index": "products", "doc_id": "1", "rating": 3},
        {"scenario_id": "sc-1", "index": "products", "doc_id": "2", "rating": 1},
    ]
    result = judgements.set(WORKSPACE_ID, items, user="test-user", via="api")

    assert result["errors"] is False
    assert len(result["items"]) == 2
    assert mock_client.bulk.call_count == 1
    assert mock_client.bulk.call_args.kwargs["refresh"] is True


def test_set_mixed_validity_batch_reports_per_item_results(monkeypatch):
    mock_client = _patch_bulk(monkeypatch)
    items = [
        {"scenario_id": "sc-1", "index": "products", "doc_id": "1", "rating": 3},
        {"scenario_id": "sc-1", "index": "products", "doc_id": "2", "rating": -1},  # invalid rating
    ]
    result = judgements.set(WORKSPACE_ID, items, user="test-user", via="api")

    assert result["errors"] is True
    statuses = [next(iter(item.values()))["status"] for item in result["items"]]
    assert statuses[0] == 200
    assert statuses[1] == 400
    # Only the valid item reached Elasticsearch.
    operations = mock_client.bulk.call_args.kwargs["operations"]
    assert len(operations) == 2  # one update action + one script body


def test_set_duplicate_scenario_index_doc_in_one_batch_resolves_to_same_id(monkeypatch):
    """Submitting the same {scenario_id, index, doc_id} twice in one call
    must not create two documents: both resolve to the same deterministic
    _id, applied as two scripted-upsert updates against the same document
    within the same `_bulk` call."""
    mock_client = _patch_bulk(monkeypatch)
    items = [
        {"scenario_id": "sc-1", "index": "products", "doc_id": "1", "rating": 2},
        {"scenario_id": "sc-1", "index": "products", "doc_id": "1", "rating": 4},
    ]
    judgements.set(WORKSPACE_ID, items, user="test-user", via="api")

    operations = mock_client.bulk.call_args.kwargs["operations"]
    action_ids = [operations[0]["update"]["_id"], operations[2]["update"]["_id"]]
    assert action_ids[0] == action_ids[1]

    expected_id = utils.unique_id([WORKSPACE_ID, "sc-1", "products", "1"])
    assert action_ids[0] == expected_id

    # Both ratings were still sent as separate scripted-upsert updates
    # within the single bulk call (second rating "wins" in Elasticsearch
    # because bulk operations apply in submission order).
    assert operations[1]["upsert"]["rating"] == 2
    assert operations[3]["upsert"]["rating"] == 4


def test_set_exceeds_max_batch_size_raises_bad_request(monkeypatch):
    _patch_bulk(monkeypatch)
    items = [
        {"scenario_id": "sc-1", "index": "products", "doc_id": str(i), "rating": 1}
        for i in range(utils.MAX_BULK_BATCH_SIZE + 1)
    ]
    with pytest.raises(BadRequest):
        judgements.set(WORKSPACE_ID, items, user="test-user", via="api")


def test_unset_single_bulk_call_with_one_refresh(monkeypatch):
    mock_client = _patch_bulk(monkeypatch)
    ids = ["j-1", "j-2", "j-3"]
    result = judgements.unset(ids)

    assert result["errors"] is False
    assert mock_client.bulk.call_count == 1
    assert mock_client.bulk.call_args.kwargs["refresh"] is True
