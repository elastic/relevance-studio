"""Unit tests for API modules es_client fallback/override behavior."""

import pytest

from server.api import workspaces, displays, content, setup
from server import utils


def _make_es_response(body, status=200):
    return type("R", (), {
        "body": body,
        "__getitem__": lambda self, k: body[k],
        "__contains__": lambda self, k: k in body,
        "get": lambda self, k, d=None: body.get(k, d),
        "meta": type("M", (), {"status": status})(),
    })()


class _MockSearchClient:
    """Mock client that records search calls."""

    def __init__(self):
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return _make_es_response({"hits": {"total": {"value": 0}, "hits": []}})

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        return _make_es_response({"_source": {"name": "test"}})


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


class TestDisplaysEsClientFallback:
    """Test that displays API uses es_client when provided, else es('studio')."""

    def test_get_uses_es_client_when_provided(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(displays, "es", lambda name: pytest.fail("es() should not be called when es_client provided"))
        displays.get("some-id", es_client=client)
        assert len(client.calls) == 1
        assert client.calls[0][0] == "get"
        assert client.calls[0][1]["id"] == "some-id"
        assert client.calls[0][1]["index"] == "esrs-displays"

    def test_get_falls_back_to_es_studio_when_es_client_none(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(displays, "es", lambda name: client if name == "studio" else pytest.fail("expected studio"))
        displays.get("some-id")
        assert len(client.calls) == 1
        assert client.calls[0][1]["id"] == "some-id"


class TestSourceIncludes:
    """Test that get() passes source_includes to ES when provided."""

    def test_workspaces_get_passes_source_includes(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(workspaces, "es", lambda name: pytest.fail("es() should not be called"))
        workspaces.get("some-id", source_includes=["name", "params"], es_client=client)
        assert len(client.calls) == 1
        assert client.calls[0][1]["source_includes"] == ["name", "params"]
        assert client.calls[0][1]["source_excludes"] == "_search"

    def test_workspaces_get_omits_source_includes_when_none(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(workspaces, "es", lambda name: pytest.fail("es() should not be called"))
        workspaces.get("some-id", es_client=client)
        assert len(client.calls) == 1
        assert "source_includes" not in client.calls[0][1]

    def test_displays_get_passes_source_includes(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(displays, "es", lambda name: pytest.fail("es() should not be called"))
        displays.get("some-id", source_includes=["index_pattern"], es_client=client)
        assert client.calls[0][1]["source_includes"] == ["index_pattern"]
        assert client.calls[0][1]["source_excludes"] == "_search"


class TestContentEsClientFallback:
    """Test that content API uses es_client when provided, else es('content')."""

    def test_search_uses_es_client_when_provided(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(content, "es", lambda name: pytest.fail("es() should not be called when es_client provided"))
        content.search("my-index-*", {"query": {"match_all": {}}}, es_client=client)
        assert len(client.calls) == 1
        assert client.calls[0][0] == "search"
        assert client.calls[0][1]["index"] == "my-index-*"

    def test_search_falls_back_to_es_content_when_es_client_none(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(content, "es", lambda name: client if name == "content" else pytest.fail("expected content"))
        content.search("my-index-*", {"query": {"match_all": {}}})
        assert len(client.calls) == 1
        assert client.calls[0][1]["index"] == "my-index-*"


class TestSetupEsClientFallback:
    """Test that setup API uses es_client when provided, else es('studio')."""

    def test_check_setup_state_uses_es_client_when_provided(self, monkeypatch):
        call_log = []

        class MockIndices:
            def get_index_template(self, **kwargs):
                call_log.append(("get_index_template", kwargs))
                return _make_es_response({"index_templates": []})

            def exists(self, **kwargs):
                call_log.append(("exists", kwargs))
                return True

        class MockClient:
            indices = MockIndices()

        monkeypatch.setattr(setup, "es", lambda name: pytest.fail("es() should not be called when es_client provided"))
        setup.check_setup_state(es_client=MockClient())
        assert len(call_log) > 0
        assert all(action in ("get_index_template", "exists") for action, _ in call_log)

    def test_check_setup_state_falls_back_to_es_studio_when_es_client_none(self, monkeypatch):
        call_log = []

        class MockIndices:
            def get_index_template(self, **kwargs):
                call_log.append(("get_index_template", kwargs))
                return _make_es_response({"index_templates": []})

            def exists(self, **kwargs):
                call_log.append(("exists", kwargs))
                return True

        class MockClient:
            indices = MockIndices()

        monkeypatch.setattr(setup, "es", lambda name: MockClient() if name == "studio" else pytest.fail("expected studio"))
        setup.check_setup_state()
        assert len(call_log) > 0


class TestUtilsSearchTagsEsClientFallback:
    """Test that utils.search_tags uses es_client when provided, else es('studio')."""

    def test_search_tags_uses_es_client_when_provided(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(utils, "es", lambda name: pytest.fail("es() should not be called when es_client provided"))
        utils.search_tags("scenarios", workspace_id="ws-1", es_client=client)
        assert len(client.calls) == 1
        assert client.calls[0][0] == "search"
        assert client.calls[0][1]["index"] == "esrs-scenarios"

    def test_search_tags_falls_back_to_es_studio_when_es_client_none(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(utils, "es", lambda name: client if name == "studio" else pytest.fail("expected studio"))
        utils.search_tags("scenarios", workspace_id="ws-1")
        assert len(client.calls) == 1


class TestUtilsSearchAssetsEsClientFallback:
    """Test that utils.search_assets uses es_client when provided, else es('studio')."""

    def test_search_assets_uses_es_client_when_provided(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(utils, "es", lambda name: pytest.fail("es() should not be called when es_client provided"))
        utils.search_assets("scenarios", workspace_id="ws-1", es_client=client)
        assert len(client.calls) >= 1
        assert client.calls[0][0] == "search"

    def test_search_assets_falls_back_to_es_studio_when_es_client_none(self, monkeypatch):
        client = _MockSearchClient()
        monkeypatch.setattr(utils, "es", lambda name: client if name == "studio" else pytest.fail("expected studio"))
        utils.search_assets("scenarios", workspace_id="ws-1")
        assert len(client.calls) >= 1
