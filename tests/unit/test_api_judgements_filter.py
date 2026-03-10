# Standard packages
from unittest.mock import MagicMock, patch

# App packages
from server.api import judgements


def _mock_es_for_search():
    """Return mock es that returns clients with empty search results."""
    mock_studio = MagicMock()
    mock_studio.search.return_value.body = {"hits": {"hits": []}}
    mock_content = MagicMock()
    mock_content.search.return_value.body = {"hits": {"hits": []}}
    mock_es = MagicMock(side_effect=lambda x: mock_studio if x == "studio" else mock_content)
    return mock_es, mock_studio


def test_search_rated_ai_uses_updated_via_mcp():
    """rated-ai filter should use @meta.updated_via == 'mcp'."""
    mock_es, mock_studio = _mock_es_for_search()
    with patch("server.api.judgements.es", mock_es):
        judgements.search(
            workspace_id="w",
            scenario_id="s",
            index_pattern="test",
            filter="rated-ai",
        )
    call_body = mock_studio.search.call_args[1]["body"]
    assert {"term": {"@meta.updated_via": "mcp"}} in call_body["query"]["bool"]["filter"]


def test_search_rated_human_excludes_updated_via_mcp():
    """rated-human filter should exclude @meta.updated_via == 'mcp'."""
    mock_es, mock_studio = _mock_es_for_search()
    with patch("server.api.judgements.es", mock_es):
        judgements.search(
            workspace_id="w",
            scenario_id="s",
            index_pattern="test",
            filter="rated-human",
        )
    call_body = mock_studio.search.call_args[1]["body"]
    assert call_body["query"]["bool"]["must_not"] == {"term": {"@meta.updated_via": "mcp"}}
