import pytest
from werkzeug.exceptions import Forbidden

from server import auth
from server.api import conversations
from server.flask import app
from server import fastmcp


class MockEsClient:
    def __init__(self, owner: str = "alice"):
        self.owner = owner
        self.last_search_body = None
        self.update_called = False
        self.delete_called = False

    def search(self, **kwargs):
        self.last_search_body = kwargs.get("body", {})
        return {"hits": {"hits": []}}

    def get(self, **kwargs):
        return {"_source": {"@meta": {"created_by": self.owner}}}

    def update(self, **kwargs):
        self.update_called = True
        return {"result": "updated"}

    def delete(self, **kwargs):
        self.delete_called = True
        return {"result": "deleted"}


def test_search_applies_created_by_filter():
    client = MockEsClient(owner="alice")

    conversations.search(
        text="",
        filters=[{"term": {"title.keyword": "chat"}}],
        user="alice",
        es_client=client,
    )

    filters = client.last_search_body["query"]["bool"]["filter"]
    assert {"term": {"@meta.created_by": "alice"}} in filters
    assert {"term": {"title.keyword": "chat"}} in filters


def test_get_forbidden_when_owner_differs():
    client = MockEsClient(owner="bob")

    with pytest.raises(Forbidden):
        conversations.get("conv-1", user="alice", es_client=client)


def test_update_requires_owner_match():
    client = MockEsClient(owner="alice")

    conversations.update("conv-1", {"title": "Updated"}, user="alice", es_client=client)
    assert client.update_called is True


def test_delete_forbidden_when_owner_differs():
    client = MockEsClient(owner="bob")

    with pytest.raises(Forbidden):
        conversations.delete("conv-1", user="alice", es_client=client)
    assert client.delete_called is False


def test_get_with_source_includes_still_checks_owner():
    """source_includes auto-adds @meta.created_by so ownership check works."""
    client = MockEsClient(owner="bob")

    with pytest.raises(Forbidden):
        conversations.get("conv-1", user="alice", source_includes=["messages"], es_client=client)


def test_get_with_source_includes_returns_when_owner_matches():
    client = MockEsClient(owner="alice")

    result = conversations.get("conv-1", user="alice", source_includes=["messages"], es_client=client)
    assert result["_source"]["@meta"]["created_by"] == "alice"


def test_flask_conversation_get_returns_403_for_other_owner(monkeypatch):
    client = app.test_client()
    mock_es_client = MockEsClient(owner="alice")

    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    monkeypatch.setattr("server.flask.es", lambda _: mock_es_client)

    response = client.get("/api/conversations/conv-1")
    assert response.status_code == 403


def test_fastmcp_conversations_search_passes_user(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        "server.fastmcp.mcp_auth.get_mcp_auth_from_context",
        lambda _ctx: ("alice", object()),
    )

    def mock_search(text, filters, sort, size, page, aggs, user=None, es_client=None):
        captured["user"] = user
        return {"hits": {"hits": []}}

    monkeypatch.setattr("server.fastmcp.api.conversations.search", mock_search)

    fastmcp.conversations_search.fn(ctx=None)
    assert captured["user"] == "alice"
