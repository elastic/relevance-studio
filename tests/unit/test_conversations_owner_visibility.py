import pytest
from werkzeug.exceptions import Forbidden

from server.client import set_request_clients
from server import auth, utils
from server.api import conversations
from server.flask import app
from server import fastmcp


class MockEsClient:
    def __init__(self, owner: str = "alice", docs: dict = None):
        """
        owner: default owner used by `get()` (single-item ownership checks
            used by conversations.get/update) and by `mget()` when `docs` is
            not given (every requested id is treated as found and owned by
            `owner`, preserving the simple single-owner mock behavior).
        docs: optional explicit per-id mapping used by `mget()`, shaped as
            `{_id: {"found": bool, "owner": str}}`, for tests that need a
            mixed batch of owned/not-owned/missing ids.
        """
        self.owner = owner
        self.docs = docs
        self.last_search_body = None
        self.update_called = False
        self.delete_called = False
        self.bulk_calls = []

    def search(self, **kwargs):
        self.last_search_body = kwargs.get("body", {})
        return {"hits": {"hits": []}}

    def get(self, **kwargs):
        return {"_source": {"@meta": {"created_by": self.owner}}}

    def mget(self, **kwargs):
        ids = kwargs.get("ids") or []
        docs = []
        for _id in ids:
            if self.docs is not None:
                entry = self.docs.get(_id)
                if entry is None or not entry.get("found", True):
                    docs.append({"found": False, "_id": _id})
                else:
                    docs.append({
                        "found": True,
                        "_id": _id,
                        "_source": {"@meta": {"created_by": entry.get("owner")}},
                    })
            else:
                docs.append({
                    "found": True,
                    "_id": _id,
                    "_source": {"@meta": {"created_by": self.owner}},
                })
        return {"docs": docs}

    def bulk(self, **kwargs):
        self.bulk_calls.append(kwargs)
        operations = kwargs.get("operations") or []
        items = []
        i = 0
        while i < len(operations):
            op = operations[i]
            action = next(iter(op))
            _id = op[action].get("_id")
            items.append({action: {"_index": op[action].get("_index"), "_id": _id, "status": 200, "result": "deleted"}})
            i += 1
        return {"took": 1, "errors": False, "items": items}

    def update(self, **kwargs):
        self.update_called = True
        return {"result": "updated"}

    def delete(self, **kwargs):
        self.delete_called = True
        return {"result": "deleted"}


def test_search_applies_created_by_filter():
    client = MockEsClient(owner="alice")
    set_request_clients(client)
    try:
        conversations.search(
            text="",
            filters=[{"term": {"title.keyword": "chat"}}],
            user="alice",
        )
    finally:
        set_request_clients(None)

    filters = client.last_search_body["query"]["bool"]["filter"]
    assert {"term": {"@meta.created_by": "alice"}} in filters
    assert {"term": {"title.keyword": "chat"}} in filters


def test_get_forbidden_when_owner_differs():
    client = MockEsClient(owner="bob")
    set_request_clients(client)
    try:
        with pytest.raises(Forbidden):
            conversations.get("conv-1", user="alice")
    finally:
        set_request_clients(None)


def test_update_requires_owner_match():
    client = MockEsClient(owner="alice")
    set_request_clients(client)
    try:
        conversations.update("conv-1", {"title": "Updated"}, user="alice")
        assert client.update_called is True
    finally:
        set_request_clients(None)


def test_delete_single_id_owned_by_caller_succeeds():
    client = MockEsClient(owner="alice")
    set_request_clients(client)
    try:
        result = conversations.delete(["conv-1"], user="alice")
    finally:
        set_request_clients(None)
    item = result["items"][0]["delete"]
    assert item["status"] == 200
    assert len(client.bulk_calls) == 1
    assert client.bulk_calls[0]["refresh"] is True


def test_delete_reports_403_when_owner_differs():
    client = MockEsClient(owner="bob")
    set_request_clients(client)
    try:
        result = conversations.delete(["conv-1"], user="alice")
    finally:
        set_request_clients(None)
    item = result["items"][0]["delete"]
    assert item["status"] == 403
    assert item["error"]["reason"] == "Conversation access denied."
    # The denied id never reached a real `_bulk` delete operation.
    assert client.bulk_calls == []


def test_delete_reports_404_when_id_is_missing():
    client = MockEsClient(docs={})
    set_request_clients(client)
    try:
        result = conversations.delete(["missing-1"], user="alice")
    finally:
        set_request_clients(None)
    item = result["items"][0]["delete"]
    assert item["status"] == 404
    assert client.bulk_calls == []


def test_delete_bulk_mixed_batch_reports_per_item_results_in_order():
    client = MockEsClient(docs={
        "owned-1": {"found": True, "owner": "alice"},
        "other-1": {"found": True, "owner": "bob"},
        "missing-1": {"found": False},
    })
    set_request_clients(client)
    try:
        result = conversations.delete(["owned-1", "other-1", "missing-1"], user="alice")
    finally:
        set_request_clients(None)

    assert result["errors"] is True
    statuses = [next(iter(item.values()))["status"] for item in result["items"]]
    assert statuses == [200, 403, 404]
    # One id was deletable, so exactly one real `_bulk` call was made (not
    # aborted by the two denied ids), with a single refresh for the batch.
    assert len(client.bulk_calls) == 1
    assert client.bulk_calls[0]["refresh"] is True


def test_collapse_denial_statuses_hides_missing_vs_forbidden():
    client = MockEsClient(docs={
        "other-1": {"found": True, "owner": "bob"},
        "missing-1": {"found": False},
    })
    set_request_clients(client)
    try:
        result = conversations.delete(["other-1", "missing-1"], user="alice")
    finally:
        set_request_clients(None)

    collapsed = utils.collapse_denial_statuses(result)
    statuses = [next(iter(item.values()))["status"] for item in collapsed["items"]]
    reasons = [next(iter(item.values()))["error"]["reason"] for item in collapsed["items"]]
    assert statuses == [403, 403]
    assert reasons == ["Conversation access denied.", "Conversation access denied."]


def test_flask_conversation_get_returns_403_for_other_owner(monkeypatch):
    client = app.test_client()
    mock_es_client = MockEsClient(owner="alice")

    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    monkeypatch.setattr("server.flask.es", lambda _: mock_es_client)

    response = client.get("/api/conversations/conv-1")
    assert response.status_code == 403


def test_flask_conversation_delete_single_item_stays_403_for_other_owner(monkeypatch):
    """Byte-identical to the pre-bulk contract: a single-item DELETE at the
    item-level path still surfaces a non-owned conversation as 403, not the
    collapsed/ambiguous shape used for multi-id and MCP requests."""
    client = app.test_client()
    mock_es_client = MockEsClient(owner="bob")

    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    monkeypatch.setattr("server.flask.es", lambda _: mock_es_client)

    response = client.delete("/api/conversations/conv-1")
    assert response.status_code == 403


def test_flask_conversation_delete_single_item_404_when_missing(monkeypatch):
    """Byte-identical to the pre-bulk contract: a single-item DELETE of a
    conversation that doesn't exist still returns 404, not the collapsed 403
    used for multi-id and MCP requests."""
    client = app.test_client()
    mock_es_client = MockEsClient(docs={})

    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    monkeypatch.setattr("server.flask.es", lambda _: mock_es_client)

    response = client.delete("/api/conversations/missing-1")
    assert response.status_code == 404


def test_flask_conversation_delete_bulk_collapses_denial_statuses(monkeypatch):
    """The collection-level bulk DELETE route collapses 404-vs-403 so a
    multi-id caller can't learn whether a conversation they don't own
    exists."""
    client = app.test_client()
    mock_es_client = MockEsClient(docs={
        "other-1": {"found": True, "owner": "bob"},
        "missing-1": {"found": False},
    })

    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    monkeypatch.setattr("server.flask.es", lambda _: mock_es_client)

    response = client.delete(
        "/api/conversations",
        json=[{"_id": "other-1"}, {"_id": "missing-1"}],
    )
    assert response.status_code == 207
    statuses = [next(iter(item.values()))["status"] for item in response.get_json()["items"]]
    assert statuses == [403, 403]


def test_fastmcp_conversations_search_passes_user(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        "server.fastmcp.mcp_auth.get_mcp_auth_from_context",
        lambda _ctx: ("alice", object()),
    )

    def mock_search(text, filters, sort, size, page, aggs, user=None):
        captured["user"] = user
        return {"hits": {"hits": []}}

    monkeypatch.setattr("server.fastmcp.api.conversations.search", mock_search)

    fastmcp.conversations_search(ctx=None)
    assert captured["user"] == "alice"
