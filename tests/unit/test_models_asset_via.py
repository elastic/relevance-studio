# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.asset import AssetCreate, AssetUpdate, _resolve_via, VALID_VIA
from server.models.workspaces import WorkspaceCreate, WorkspaceUpdate
from tests.utils import assert_valid_meta_for_create_request, assert_valid_meta_for_update_request, mock_context

def mock_input_create():
    return {
        "name": "Test",
        "index_pattern": "test",
        "params": ["text"],
        "rating_scale": {"min": 0, "max": 4},
    }

def mock_input_update():
    return {"name": "Updated"}


def test_resolve_via_defaults_to_api_when_not_provided():
    assert _resolve_via(None) == "api"
    assert _resolve_via({}) == "api"
    assert _resolve_via({"user": "x"}) == "api"


def test_resolve_via_valid_values():
    for via in VALID_VIA:
        assert _resolve_via({"via": via}) == via


def test_resolve_via_invalid_raises():
    with pytest.raises(ValueError, match="via must be one of"):
        _resolve_via({"via": "invalid"})
    with pytest.raises(ValueError, match="via must be one of"):
        _resolve_via({"via": ""})
    with pytest.raises(ValueError, match="via must be one of"):
        _resolve_via({"via": "ai"})


def test_asset_create_default_via():
    model = WorkspaceCreate.model_validate(mock_input_create(), context={"user": "u"})
    assert model.meta.get("created_via") == "api"
    assert model.meta.get("updated_via") is None


def test_asset_create_via_server():
    model = WorkspaceCreate.model_validate(mock_input_create(), context=mock_context(via="server"))
    assert_valid_meta_for_create_request(model.meta, mock_context()["user"], created_via="server")


def test_asset_create_via_mcp():
    model = WorkspaceCreate.model_validate(mock_input_create(), context=mock_context(via="mcp"))
    assert model.meta.get("created_via") == "mcp"


def test_asset_update_default_via():
    model = WorkspaceUpdate.model_validate(mock_input_update(), context={"user": "u"})
    assert model.meta.get("updated_via") == "api"


def test_asset_update_via_mcp():
    model = WorkspaceUpdate.model_validate(mock_input_update(), context=mock_context(via="mcp"))
    assert_valid_meta_for_update_request(model.meta, mock_context()["user"], updated_via="mcp")


def test_asset_create_invalid_via_raises():
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate(mock_input_create(), context={"user": "u", "via": "bad"})


def test_asset_update_invalid_via_raises():
    with pytest.raises(ValidationError):
        WorkspaceUpdate.model_validate(mock_input_update(), context={"user": "u", "via": "bad"})
