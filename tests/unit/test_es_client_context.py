"""Unit tests for request-scoped Elasticsearch client behavior via ContextVar."""

import pytest
from server.client import es, set_request_clients
from server.api import workspaces, content

def _make_es_response(body, status=200):
    return type("R", (), {
        "body": body,
        "__getitem__": lambda self, k: body[k],
        "__contains__": lambda self, k: k in body,
        "get": lambda self, k, d=None: body.get(k, d),
        "meta": type("M", (), {"status": status})(),
    })()

class MockClient:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        return _make_es_response({"_source": {"name": self.name}})

    def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return _make_es_response({"hits": {"total": {"value": 0}, "hits": []}})

def test_es_prefers_request_scoped_client():
    studio_mock = MockClient("request-studio")
    set_request_clients(studio_mock)
    
    try:
        client = es("studio")
        assert client is studio_mock
        
        # API call should use the mock
        workspaces.get("some-id")
        assert len(studio_mock.calls) == 1
        assert studio_mock.calls[0][1]["id"] == "some-id"
    finally:
        set_request_clients(None)

def test_es_falls_back_to_singleton_when_no_request_context(monkeypatch):
    singleton_mock = MockClient("singleton-studio")
    
    # We need to mock _setup_clients to return our mock
    monkeypatch.setattr("server.client._setup_clients", lambda: {"studio": singleton_mock, "content": singleton_mock})
    monkeypatch.setattr("server.client._es_clients", None) # Force re-setup
    
    set_request_clients(None)
    
    client = es("studio")
    assert client is singleton_mock

def test_content_client_determined_by_deployment_sharing(monkeypatch):
    studio_singleton = MockClient("studio-singleton")
    content_singleton = MockClient("content-singleton")
    
    # Case 1: Shared deployment
    # By setting _es_clients, we simulate that setup has already happened and they are shared.
    monkeypatch.setattr("server.client._es_clients", {"studio": studio_singleton, "content": studio_singleton})
    
    user_client = MockClient("user-client")
    set_request_clients(user_client)
    
    try:
        assert es("studio") is user_client
        assert es("content") is user_client # Should follow studio if shared
    finally:
        set_request_clients(None)

    # Case 2: Separate deployment
    # By setting _es_clients, we simulate they are separate.
    monkeypatch.setattr("server.client._es_clients", {"studio": studio_singleton, "content": content_singleton})
    
    set_request_clients(user_client)
    
    try:
        assert es("studio") is user_client
        assert es("content") is content_singleton # Should stay singleton if separate
    finally:
        set_request_clients(None)
