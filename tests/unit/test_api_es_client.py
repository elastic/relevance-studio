"""Unit tests for API modules es_client fallback/override behavior."""

import pytest

from server.api import workspaces


class TestWorkspacesEsClientFallback:
    """Test that workspaces API uses es_client when provided, else es('studio')."""

    def test_get_uses_es_client_when_provided(self, monkeypatch):
        call_args = []

        class MockClient:
            def get(self, **kwargs):
                call_args.append(("get", kwargs))
                return type("R", (), {"body": {"_source": {"name": "test"}}, "meta": type("M", (), {"status": 200})()})()

        monkeypatch.setattr(workspaces, "es", lambda name: pytest.fail("es() should not be called when es_client provided"))
        client = MockClient()
        result = workspaces.get("some-id", es_client=client)
        assert len(call_args) == 1
        assert call_args[0][0] == "get"
        assert call_args[0][1]["id"] == "some-id"
        assert call_args[0][1]["index"] == "esrs-workspaces"

    def test_get_falls_back_to_es_studio_when_es_client_none(self, monkeypatch):
        call_args = []

        class MockClient:
            def get(self, **kwargs):
                call_args.append(("get", kwargs))
                return type("R", (), {"body": {"_source": {"name": "test"}}, "meta": type("M", (), {"status": 200})()})()

        monkeypatch.setattr(workspaces, "es", lambda name: MockClient() if name == "studio" else pytest.fail("expected studio"))
        result = workspaces.get("some-id")
        assert len(call_args) == 1
        assert call_args[0][1]["id"] == "some-id"
