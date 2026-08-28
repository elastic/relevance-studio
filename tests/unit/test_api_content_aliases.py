# Standard packages
from unittest.mock import MagicMock, patch

# App packages
from server.api import content


def _mock_es(response):
    """Return mock es whose content client returns the given get_alias response."""
    mock_content = MagicMock()
    mock_content.options.return_value.indices.get_alias.return_value = response
    return MagicMock(return_value=mock_content), mock_content


def test_aliases_maps_indices_to_sorted_alias_names():
    response = MagicMock()
    response.get.return_value = None
    response.body = {
        "products-000002": {"aliases": {"products": {}, "current": {}}},
        "products-000001": {"aliases": {"products": {}}},
    }
    mock_es, mock_content = _mock_es(response)
    with patch("server.api.content.es", mock_es):
        result = content.aliases("products-*")
    assert result == {
        "products-000001": ["products"],
        "products-000002": ["current", "products"],
    }
    kwargs = mock_content.options.return_value.indices.get_alias.call_args[1]
    assert kwargs["index"] == "products-*"
    # A missing index in a comma-separated pattern must not discard the aliases
    # of the indices that do exist.
    assert kwargs["ignore_unavailable"] is True
    assert mock_content.options.call_args[1]["ignore_status"] == 404


def test_aliases_returns_empty_list_for_index_without_aliases():
    response = MagicMock()
    response.get.return_value = None
    response.body = {"movies": {"aliases": {}}}
    mock_es, _ = _mock_es(response)
    with patch("server.api.content.es", mock_es):
        assert content.aliases("movies") == {"movies": []}


def test_aliases_returns_empty_dict_when_index_pattern_not_found():
    """The body of a 404 is an error document, not indices, and must be discarded."""
    response = MagicMock()
    # Only "status" reports 404; the body also carries keys that would be read as
    # indices if the guard were dropped.
    response.get.side_effect = lambda key, default=None: 404 if key == "status" else default
    response.body = {
        "status": 404,
        "error": {"type": "index_not_found_exception", "index": "missing"},
    }
    mock_es, _ = _mock_es(response)
    with patch("server.api.content.es", mock_es):
        assert content.aliases("missing-*") == {}


def test_aliases_keeps_existing_indices_when_one_is_missing():
    """ignore_unavailable lets Elasticsearch return the indices that do exist."""
    response = MagicMock()
    response.get.return_value = None
    response.body = {"products-000001": {"aliases": {"products": {}}}}
    mock_es, _ = _mock_es(response)
    with patch("server.api.content.es", mock_es):
        assert content.aliases("products,archived-products") == {
            "products-000001": ["products"]
        }
