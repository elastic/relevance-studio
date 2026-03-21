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


def test_search_rated_ai_matches_via_mcp_or_by_ai():
    """rated-ai filter should match @meta.updated_via=='mcp' OR @meta.updated_by=='ai'."""
    mock_es, mock_studio = _mock_es_for_search()
    with patch("server.api.judgements.es", mock_es):
        judgements.search(
            workspace_id="w",
            scenario_id="s",
            index_pattern="test",
            filter="rated-ai",
        )
    call_body = mock_studio.search.call_args[1]["body"]
    ai_clause = call_body["query"]["bool"]["filter"][-1]
    assert "bool" in ai_clause
    should = ai_clause["bool"]["should"]
    assert {"term": {"@meta.updated_via": "mcp"}} in should
    assert {"term": {"@meta.updated_by": "ai"}} in should
    assert ai_clause["bool"]["minimum_should_match"] == 1


def test_search_rated_human_excludes_via_mcp_and_by_ai():
    """rated-human filter should exclude @meta.updated_via=='mcp' AND @meta.updated_by=='ai'."""
    mock_es, mock_studio = _mock_es_for_search()
    with patch("server.api.judgements.es", mock_es):
        judgements.search(
            workspace_id="w",
            scenario_id="s",
            index_pattern="test",
            filter="rated-human",
        )
    call_body = mock_studio.search.call_args[1]["body"]
    must_not = call_body["query"]["bool"]["must_not"]
    assert {"term": {"@meta.updated_via": "mcp"}} in must_not
    assert {"term": {"@meta.updated_by": "ai"}} in must_not
