# Third-party packages
import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import BadRequest

# App packages
from server import utils
from server.api import benchmarks, scenarios, workspaces


def _patch_delete_by_query(monkeypatch, module):
    mock_client = MagicMock()
    mock_client.delete_by_query.return_value = {"took": 1, "deleted": 0, "failures": []}
    monkeypatch.setattr(module, "es", lambda _: mock_client)
    return mock_client


def test_workspaces_delete_widens_term_to_terms_for_multiple_ids(monkeypatch):
    mock_client = _patch_delete_by_query(monkeypatch, workspaces)
    ids = ["ws-1", "ws-2", "ws-3"]

    result = workspaces.delete(ids)

    assert result == mock_client.delete_by_query.return_value
    # The first delete_by_query call covers the cascade indices in one shot,
    # regardless of how many ids were given.
    body = mock_client.delete_by_query.call_args_list[0].kwargs["body"]
    should = body["query"]["bool"]["should"]
    terms_clauses = [
        clause["bool"]["filter"][1] for clause in should
    ]
    for clause in terms_clauses:
        assert "terms" in clause
        field = next(iter(clause["terms"]))
        assert clause["terms"][field] == ids


def test_workspaces_delete_sweeps_data_streams_with_terms(monkeypatch):
    mock_client = _patch_delete_by_query(monkeypatch, workspaces)
    ids = ["ws-1", "ws-2"]

    workspaces.delete(ids)

    # One call for the cascade indices, then one per data stream swept.
    stream_bodies = [
        call.kwargs["body"] for call in mock_client.delete_by_query.call_args_list[1:]
    ]
    assert len(stream_bodies) == 8  # see workspaces.delete's stream tuple
    for body in stream_bodies:
        assert body["query"]["terms"]["workspace_id"] == ids


def test_workspaces_delete_exceeds_max_batch_size_raises_bad_request(monkeypatch):
    _patch_delete_by_query(monkeypatch, workspaces)
    ids = [f"ws-{i}" for i in range(utils.MAX_BULK_BATCH_SIZE + 1)]
    with pytest.raises(BadRequest):
        workspaces.delete(ids)


def test_scenarios_delete_widens_term_to_terms_for_multiple_ids(monkeypatch):
    mock_client = _patch_delete_by_query(monkeypatch, scenarios)
    ids = ["sc-1", "sc-2"]

    scenarios.delete(ids)

    assert mock_client.delete_by_query.call_count == 1
    body = mock_client.delete_by_query.call_args.kwargs["body"]
    should = body["query"]["bool"]["should"]
    assert should[0]["bool"]["filter"][1]["terms"]["_id"] == ids
    assert should[1]["bool"]["filter"][1]["terms"]["scenario_id"] == ids


def test_benchmarks_delete_widens_term_to_terms_for_multiple_ids(monkeypatch):
    mock_client = _patch_delete_by_query(monkeypatch, benchmarks)
    ids = ["bm-1", "bm-2"]

    benchmarks.delete(ids)

    # First call: configs + runs cascade.
    first_body = mock_client.delete_by_query.call_args_list[0].kwargs["body"]
    should = first_body["query"]["bool"]["should"]
    assert should[0]["bool"]["filter"][1]["terms"]["_id"] == ids
    assert should[1]["bool"]["filter"][1]["terms"]["benchmark_id"] == ids

    # Remaining calls: per-data-stream sweeps, also widened to `terms`.
    stream_bodies = [
        call.kwargs["body"] for call in mock_client.delete_by_query.call_args_list[1:]
    ]
    assert len(stream_bodies) == 8
    for body in stream_bodies:
        assert body["query"]["terms"]["benchmark_id"] == ids
