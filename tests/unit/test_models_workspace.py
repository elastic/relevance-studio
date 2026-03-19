# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.workspaces import WorkspaceCreate, WorkspaceUpdate
from tests.utils import (
    assert_valid_meta_for_create_request,
    assert_valid_meta_for_update_request,
    invalid_values_for,
    mock_context,
)

def mock_input_create():
    """
    Returns a mock input with all required and optional fields for creates.
    """
    input = {
        "name": "Products",
        "index_pattern": "products",
        "params": [
            "text",
            "country_code",
        ],
        "rating_scale": {
            "min": 0,
            "max": 4,
        },
        "description": "Project goals and collaboration guidance.",
        "tags": [
            "test",
        ],
    }
    return input

def mock_input_update():
    """
    Returns a mock input with all required and optional fields for updates.
    """
    input = mock_input_create()
    input.pop("rating_scale", None)
    return input

####  Test Validation of Input Structure  ######################################

def test_create_is_invalid_without_required_inputs():
    
    # "name" is required in the input for creates
    input = mock_input_create()
    input.pop("name", None)
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate(input, context=mock_context())
    
    # "index_pattern" is required in the input for creates
    input = mock_input_create()
    input.pop("index_pattern", None)
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate(input, context=mock_context())
    
    # "params" is required in the input for creates
    input = mock_input_create()
    input.pop("params", None)
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate(input, context=mock_context())
    
    # "rating_scale" is required in the input for creates
    input = mock_input_create()
    input.pop("rating_scale", None)
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate(input, context=mock_context())

def test_update_is_invalid_without_required_inputs():
    
    # workspace updates have no required inputs
    pass

def test_create_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for creates
    input = mock_input_create()
    input["@meta"] = {"created_at": "invalid", "created_by": "should-fail"}
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate(input, context=mock_context())

def test_update_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for updates
    input = mock_input_update()
    input["@meta"] = {"updated_at": "invalid", "updated_by": "should-fail"}
    with pytest.raises(ValidationError):
        WorkspaceUpdate.model_validate(input, context=mock_context())
    
    # "rating_scale" is forbidden in the input for updates
    input = mock_input_update()
    input["rating_scale"] = mock_input_create()["rating_scale"]
    with pytest.raises(ValidationError):
        WorkspaceUpdate.model_validate(input, context=mock_context())

def test_create_is_valid_without_optional_inputs():
    
    # "description" is optional in the input for creates
    input = mock_input_create()
    input.pop("description", None)
    model = WorkspaceCreate.model_validate(input, context=mock_context())
    assert model.description == ""

    # "tags" is optional in the input for creates
    input = mock_input_create()
    input.pop("tags", None)
    model = WorkspaceCreate.model_validate(input, context=mock_context())

def test_update_is_valid_without_optional_inputs():
    
    # "name" is optional in the input for updates
    input = mock_input_update()
    input.pop("name", None)
    model = WorkspaceUpdate.model_validate(input, context=mock_context())
    assert model.name is None
    
    # "index_pattern" is optional in the input for updates
    input = mock_input_update()
    input.pop("index_pattern", None)
    model = WorkspaceUpdate.model_validate(input, context=mock_context())
    assert model.index_pattern is None
    
    # "params" is optional in the input for updates
    input = mock_input_update()
    input.pop("params", None)
    model = WorkspaceUpdate.model_validate(input, context=mock_context())
    assert model.params is None
    
    # "tags" is optional in the input for updates
    input = mock_input_update()
    input.pop("tags", None)
    model = WorkspaceUpdate.model_validate(input, context=mock_context())
    assert model.tags is None

    # "description" is optional in the input for updates
    input = mock_input_update()
    input.pop("description", None)
    model = WorkspaceUpdate.model_validate(input, context=mock_context())
    assert model.description is None
    
def test_create_is_invalid_with_unexpected_inputs():
    input = mock_input_create()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate(input, context=mock_context())
        
def test_update_is_invalid_with_unexpected_inputs():
    input = mock_input_update()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        WorkspaceUpdate.model_validate(input, context=mock_context())
    
####  Test Validation of Input Values  #########################################
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_name(value):
    input = mock_input_create()
    input["name"] = value
    with pytest.raises(ValidationError):
        WorkspaceCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_name(value):
    input = mock_input_update()
    input["name"] = value
    with pytest.raises(ValidationError):
        WorkspaceUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_index_pattern(value):
    input = mock_input_create()
    input["index_pattern"] = value
    with pytest.raises(ValidationError):
        WorkspaceCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_index_pattern(value):
    input = mock_input_update()
    input["index_pattern"] = value
    with pytest.raises(ValidationError):
        WorkspaceUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings"))
def test_create_handles_invalid_inputs_for_params(value):
    input = mock_input_create()
    input["params"] = value
    with pytest.raises(ValidationError):
        WorkspaceCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_params(value):
    input = mock_input_create()
    input["params"] = value
    with pytest.raises(ValidationError):
        WorkspaceUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_0"))
def test_create_handles_invalid_inputs_for_rating_scale_min(value):
    input = mock_input_create()
    input["rating_scale"]["min"] = value
    with pytest.raises(ValidationError):
        WorkspaceCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_1"))
def test_create_handles_invalid_inputs_for_rating_scale_max(value):
    input = mock_input_create()
    input["rating_scale"]["max"] = value
    with pytest.raises(ValidationError):
        WorkspaceCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_tags(value):
    input = mock_input_create()
    input["tags"] = value
    with pytest.raises(ValidationError):
        WorkspaceCreate(**input)
        
@pytest.mark.parametrize("value", [[],["test"]])
def test_create_handles_valid_inputs_for_tags(value):
    input = mock_input_create()
    input["tags"] = value
    WorkspaceCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_tags(value):
    input = mock_input_update()
    input["tags"] = value
    with pytest.raises(ValidationError):
        WorkspaceUpdate(**input)
        
@pytest.mark.parametrize("value", [[],["test"]])
def test_update_handles_valid_inputs_for_tags(value):
    input = mock_input_update()
    input["tags"] = value
    WorkspaceUpdate(**input)

@pytest.mark.parametrize("value", invalid_values_for("string", allow_empty=True))
def test_create_handles_invalid_inputs_for_description(value):
    input = mock_input_create()
    input["description"] = value
    with pytest.raises(ValidationError):
        WorkspaceCreate(**input)

@pytest.mark.parametrize("value", [v for v in invalid_values_for("string", allow_empty=True) if v is not None])
def test_update_handles_invalid_inputs_for_description(value):
    input = mock_input_update()
    input["description"] = value
    with pytest.raises(ValidationError):
        WorkspaceUpdate(**input)
    
####  Test Creation of Computed Fields  ########################################

def test_create_computes_meta():
    model = WorkspaceCreate.model_validate(mock_input_create(), context=mock_context())
    assert_valid_meta_for_create_request(model.meta, mock_context()["user"])

def test_update_computes_meta():
    model = WorkspaceUpdate.model_validate(mock_input_update(), context=mock_context())
    assert_valid_meta_for_update_request(model.meta, mock_context()["user"])
    
####  Test Serialization  ######################################################
    
def test_create_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_create()
    model = WorkspaceCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert serialized["name"] == mock_input_create()["name"]
    assert serialized["index_pattern"] == mock_input_create()["index_pattern"]
    assert sorted(serialized["params"]) == sorted(mock_input_create()["params"])
    assert serialized["rating_scale"]["min"] == mock_input_create()["rating_scale"]["min"]
    assert serialized["rating_scale"]["max"] == mock_input_create()["rating_scale"]["max"]
    assert serialized["description"] == mock_input_create()["description"]
    assert sorted(serialized["tags"]) == sorted(mock_input_create()["tags"])
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_create_request(serialized["@meta"], mock_context()["user"])
    
def test_create_serialization_initializes_omitted_optional_inputs():
    
    # Use mock input without optional fields
    input = mock_input_create()
    input.pop("description", None)
    input.pop("tags", None)
    
    model = WorkspaceCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert serialized["description"] == ""
    assert sorted(serialized["tags"]) == []
    
def test_update_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_update()
    model = WorkspaceUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert serialized["name"] == mock_input_update()["name"]
    assert serialized["index_pattern"] == mock_input_update()["index_pattern"]
    assert sorted(serialized["params"]) == sorted(mock_input_update()["params"])
    assert serialized["description"] == mock_input_update()["description"]
    assert sorted(serialized["tags"]) == sorted(mock_input_update()["tags"])
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update_request(serialized["@meta"], mock_context()["user"])

def test_update_serialization_omits_omitted_optional_inputs():
    
    # Use mock input without optional fields
    input = mock_input_update()
    input.pop("name", None)
    input.pop("index_pattern", None)
    input.pop("params", None)
    input.pop("description", None)
    input.pop("tags", None)
    model = WorkspaceUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that omitted optional inputs are not in serialized output
    assert "name" not in serialized
    assert "index_pattern" not in serialized
    assert "description" not in serialized
    assert "tags" not in serialized
    assert "params" not in serialized or serialized["params"] is None
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update_request(serialized["@meta"], mock_context()["user"])