# Third-party packages
import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import BadRequest

# App packages
from server import utils
from server.api import displays, judgements, strategies
from tests.utils import make_fake_bulk_response

# Plain-bulk deletes: no model, no ownership check, just N `delete` actions
# collapsed into a single `_bulk` call (see §2.3 / §3 of the plan).
MODULES = {
    "displays": (displays, "esrs-displays"),
    "strategies": (strategies, "esrs-strategies"),
    "judgements": (judgements, "esrs-judgements"),
}


def _patch_bulk(monkeypatch, module):
    mock_client = MagicMock()
    mock_client.bulk.side_effect = lambda **kwargs: make_fake_bulk_response(kwargs.get("operations") or [])
    monkeypatch.setattr(module, "es", lambda _: mock_client)
    return mock_client


def _delete(module, ids):
    # judgements exposes `unset`, the others expose `delete`.
    fn = getattr(module, "unset", None) or getattr(module, "delete")
    return fn(ids)


@pytest.mark.parametrize("key", MODULES.keys())
def test_bulk_delete_single_bulk_call_with_one_refresh(monkeypatch, key):
    module, index_name = MODULES[key]
    mock_client = _patch_bulk(monkeypatch, module)

    ids = ["id-1", "id-2", "id-3"]
    result = _delete(module, ids)

    assert result["errors"] is False
    assert len(result["items"]) == 3
    returned_ids = [next(iter(item.values()))["_id"] for item in result["items"]]
    assert returned_ids == ids

    assert mock_client.bulk.call_count == 1
    assert mock_client.bulk.call_args.kwargs["refresh"] is True
    operations = mock_client.bulk.call_args.kwargs["operations"]
    assert len(operations) == 3  # delete actions have no source line
    for op, _id in zip(operations, ids):
        assert op["delete"]["_index"] == index_name
        assert op["delete"]["_id"] == _id


@pytest.mark.parametrize("key", MODULES.keys())
def test_bulk_delete_exceeds_max_batch_size_raises_bad_request(monkeypatch, key):
    module, _ = MODULES[key]
    _patch_bulk(monkeypatch, module)
    ids = [f"id-{i}" for i in range(utils.MAX_BULK_BATCH_SIZE + 1)]
    with pytest.raises(BadRequest):
        _delete(module, ids)
