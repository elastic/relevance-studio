# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.displays import DisplayCreate, DisplayUpdate
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
        "workspace_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "index_pattern": "products",
        "template": {
            "body": """### {{name.text}}
    *{{category.keyword}}*
    {{description.text}}""",
            "image": {
                "position": "top-right",
                "url": "http://{{hostname}}:8080/{{_id}}.png"
            }
        }
    }
    return input

def mock_input_update():
    """
    Returns a mock input with all required and optional fields for updates.
    """
    input = mock_input_create()
    input.pop("index_pattern")
    return input

####  Test Validation of Input Structure  ######################################

def test_create_is_invalid_without_required_inputs():
    
    # "workspace_id" is required in the input for creates
    input = mock_input_create()
    input.pop("workspace_id", None)
    with pytest.raises(ValidationError):
        DisplayCreate.model_validate(input, context=mock_context())
    
    # "index_pattern" is required in the input for creates
    input = mock_input_create()
    input.pop("index_pattern", None)
    with pytest.raises(ValidationError):
        DisplayCreate.model_validate(input, context=mock_context())

def test_update_is_invalid_without_required_inputs():
    
    # "workspace_id" is required in the input for updates
    input = mock_input_create()
    input.pop("workspace_id", None)
    with pytest.raises(ValidationError):
        DisplayUpdate.model_validate(input, context=mock_context())

def test_create_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for creates
    input = mock_input_create()
    input["@meta"] = {"created_at": "invalid", "created_by": "should-fail"}
    with pytest.raises(ValidationError):
        DisplayCreate.model_validate(input, context=mock_context())
    
    # "fields" is forbidden in the input for creates
    input = mock_input_update()
    input["fields"] = ["should-not", "be-here"]
    with pytest.raises(ValidationError):
        DisplayUpdate.model_validate(input, context=mock_context())

def test_update_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for updates
    input = mock_input_update()
    input["@meta"] = {"updated_at": "invalid", "updated_by": "should-fail"}
    with pytest.raises(ValidationError):
        DisplayUpdate.model_validate(input, context=mock_context())
    
    # "fields" is forbidden in the input for updates
    input = mock_input_update()
    input["fields"] = ["should-not", "be-here"]
    with pytest.raises(ValidationError):
        DisplayUpdate.model_validate(input, context=mock_context())

def test_create_is_valid_without_optional_inputs():
    
    # "template" is optional in the input for creates
    input = mock_input_create()
    input.pop("template", None)
    model = DisplayCreate.model_validate(input, context=mock_context())
    
    # creates must initialize optional fields that were omitted in the input
    assert model.template == {}
    assert model.fields == []

def test_update_is_valid_without_optional_inputs():
    
    # "index_pattern" is optional in the input for updates
    input = mock_input_update()
    input.pop("index_pattern", None)
    model = DisplayUpdate.model_validate(input, context=mock_context())
    assert model.index_pattern is None
    
    # "template" is optional in the input for updates
    input = mock_input_update()
    input.pop("template", None)
    model = DisplayUpdate.model_validate(input, context=mock_context())
    assert model.template is None
    assert model.fields is None
    
def test_create_is_invalid_with_unexpected_inputs():
    input = mock_input_create()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        DisplayCreate.model_validate(input, context=mock_context())
        
def test_update_is_invalid_with_unexpected_inputs():
    input = mock_input_update()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        DisplayUpdate.model_validate(input, context=mock_context())
    
####  Test Validation of Input Values  #########################################
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_workspace_id(value):
    input = mock_input_create()
    input["workspace_id"] = value
    with pytest.raises(ValidationError):
        DisplayCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_workspace_id(value):
    input = mock_input_update()
    input["workspace_id"] = value
    with pytest.raises(ValidationError):
        DisplayUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_index_pattern(value):
    input = mock_input_create()
    input["index_pattern"] = value
    with pytest.raises(ValidationError):
        DisplayCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_index_pattern(value):
    input = mock_input_update()
    input["index_pattern"] = value
    with pytest.raises(ValidationError):
        DisplayUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_create_handles_invalid_inputs_for_template(value):
    input = mock_input_create()
    input["template"] = value
    with pytest.raises(ValidationError):
        DisplayCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_template(value):
    input = mock_input_update()
    input["template"] = value
    with pytest.raises(ValidationError):
        DisplayUpdate(**input)
    
####  Test Creation of Computed Fields  ########################################

def test_create_computes_meta():
    model = DisplayCreate.model_validate(mock_input_create(), context=mock_context())
    assert_valid_meta_for_create_request(model.meta, mock_context()["user"])

def test_update_computes_meta():
    model = DisplayUpdate.model_validate(mock_input_update(), context=mock_context())
    assert_valid_meta_for_update_request(model.meta, mock_context()["user"])

def test_create_computes_fields_from_template():
    
    # "fields" must have the params extracted from "template.body"
    input = mock_input_create()
    model = DisplayCreate.model_validate(input, context=mock_context())
    assert sorted(model.fields) == sorted([
        "name.text", "category.keyword", "description.text", "hostname",
    ])
    
    # "fields" must be initialized with an empty list if "template.body" is omitted
    input = mock_input_create()
    input.pop("template", None)
    model = DisplayCreate.model_validate(input, context=mock_context())
    assert model.fields == []
    
    # "fields" must be initialized with an empty list if "template.body" is empty
    input = mock_input_create()
    input["template"] = {
        "body": {}
    }
    model = DisplayCreate.model_validate(input, context=mock_context())
    assert model.fields == []

def test_update_computes_fields_from_template():
    
    # "fields" must have the params extracted from "template.body"
    input = mock_input_update()
    model = DisplayUpdate.model_validate(input, context=mock_context())
    assert sorted(model.fields) == sorted([
        "name.text", "category.keyword", "description.text", "hostname",
    ])
    
    # "fields" must be omitted if the input omits "template",
    # because the user is not requesting a change to "template".
    input = mock_input_update()
    input.pop("template", None)
    model = DisplayUpdate.model_validate(input, context=mock_context())
    assert model.fields is None
    
    # "fields" must be empty if the input has an empty "template",
    # because the user is requesting that "template" be changed to empty.
    input = mock_input_update()
    input["template"] = {}
    model = DisplayUpdate.model_validate(input, context=mock_context())
    assert model.fields == []
    
####  Test Serialization  ######################################################
    
def test_create_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_create()
    model = DisplayCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert serialized["workspace_id"] == mock_input_create()["workspace_id"]
    assert serialized["index_pattern"] == mock_input_create()["index_pattern"]
    assert "template" in serialized
    assert sorted(serialized["fields"]) == sorted([
        "category.keyword", "description.text", "name.text", "hostname",
    ])
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_create_request(serialized.get("@meta"), mock_context()["user"])
    
def test_create_serialization_initializes_omitted_optional_inputs():
    
    # Use mock input without optional fields
    input = mock_input_create()
    input.pop("template", None)
    model = DisplayCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that omitted optional inputs were initialized in the serialized output
    assert serialized["template"] == {}
    assert serialized["fields"] == []
    
def test_update_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_update()
    model = DisplayUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert serialized["workspace_id"] == mock_input_update()["workspace_id"]
    assert "index_pattern" not in serialized
    assert "template" in serialized
    assert sorted(serialized["fields"]) == sorted([
        "name.text", "category.keyword", "description.text", "hostname",
    ])
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update_request(serialized.get("@meta"), mock_context()["user"])

def test_update_serialization_omits_omitted_optional_inputs():
    
    # Use mock input without optional fields
    input = mock_input_update()
    input.pop("index_pattern", None)
    input.pop("template", None)
    model = DisplayUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that omitted optional inputs are not in serialized output
    assert "index_pattern" not in serialized
    assert "template" not in serialized
    assert "fields" not in serialized or serialized["fields"] is None
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update_request(serialized.get("@meta"), mock_context()["user"])