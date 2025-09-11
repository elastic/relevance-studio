# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.strategies import StrategyCreate, StrategyUpdate
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
        "name": "Classical - Name match",
        "tags": [
            "bm25",
        ],
        "template": {
            "lang": "mustache",
            "source": """{"retriever":{"standard":{"query":{"match":{"name.text":{"query":"{{ text }}"}}}}}}""",
        }
    }
    return input

def mock_input_update():
    """
    Returns a mock input with all required and optional fields for updates.
    """
    input = mock_input_create()
    return input

####  Test Validation of Input Structure  ######################################

def test_create_is_invalid_without_required_inputs():
    
    # "workspace_id" is required in the input for creates
    input = mock_input_create()
    input.pop("workspace_id", None)
    with pytest.raises(ValidationError):
        StrategyCreate.model_validate(input, context=mock_context())
    
    # "name" is required in the input for creates
    input = mock_input_create()
    input.pop("name", None)
    with pytest.raises(ValidationError):
        StrategyCreate.model_validate(input, context=mock_context())

def test_update_is_invalid_without_required_inputs():
    
    # "workspace_id" is required in the input for updates
    input = mock_input_create()
    input.pop("workspace_id", None)
    with pytest.raises(ValidationError):
        StrategyUpdate.model_validate(input, context=mock_context())

def test_create_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for creates
    input = mock_input_create()
    input["@meta"] = {"created_at": "invalid", "created_by": "should-fail"}
    with pytest.raises(ValidationError):
        StrategyCreate.model_validate(input, context=mock_context())
    
    # "params" is forbidden in the input for creates
    input = mock_input_update()
    input["params"] = ["should-not", "be-here"]
    with pytest.raises(ValidationError):
        StrategyUpdate.model_validate(input, context=mock_context())

def test_update_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for updates
    input = mock_input_update()
    input["@meta"] = {"updated_at": "invalid", "updated_by": "should-fail"}
    with pytest.raises(ValidationError):
        StrategyUpdate.model_validate(input, context=mock_context())
    
    # "params" is forbidden in the input for updates
    input = mock_input_update()
    input["params"] = ["should-not", "be-here"]
    with pytest.raises(ValidationError):
        StrategyUpdate.model_validate(input, context=mock_context())

def test_create_is_valid_without_optional_inputs():
    
    # "tags" is optional in the input for creates
    input = mock_input_create()
    input.pop("tags", None)
    model = StrategyCreate.model_validate(input, context=mock_context())
    
    # creates must initialize optional fields that were omitted in the input
    assert model.tags == []
    
    # "template" is optional in the input for updates
    input = mock_input_create()
    input.pop("template", None)
    model = StrategyCreate.model_validate(input, context=mock_context())
    
    # creates must initialize optional fields that were omitted in the input
    assert model.template.lang == "mustache"
    assert model.template.source == ""
    assert model.params == []

def test_update_is_valid_without_optional_inputs():
    
    # "name" is optional in the input for updates
    input = mock_input_update()
    input.pop("name", None)
    model = StrategyUpdate.model_validate(input, context=mock_context())
    assert model.name is None
    
    # "tags" is optional in the input for updates
    input = mock_input_update()
    input.pop("tags", None)
    model = StrategyUpdate.model_validate(input, context=mock_context())
    assert model.tags is None
    
    # "template" is optional in the input for updates
    input = mock_input_update()
    input.pop("template", None)
    model = StrategyUpdate.model_validate(input, context=mock_context())
    assert model.template is None
    assert model.params is None
    
def test_create_is_invalid_with_unexpected_inputs():
    input = mock_input_create()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        StrategyCreate.model_validate(input, context=mock_context())
        
def test_update_is_invalid_with_unexpected_inputs():
    input = mock_input_update()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        StrategyUpdate.model_validate(input, context=mock_context())
    
####  Test Validation of Input Values  #########################################
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_workspace_id(value):
    input = mock_input_create()
    input["workspace_id"] = value
    with pytest.raises(ValidationError):
        StrategyCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_workspace_id(value):
    input = mock_input_update()
    input["workspace_id"] = value
    with pytest.raises(ValidationError):
        StrategyUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_name(value):
    input = mock_input_create()
    input["name"] = value
    with pytest.raises(ValidationError):
        StrategyCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_name(value):
    input = mock_input_update()
    input["name"] = value
    with pytest.raises(ValidationError):
        StrategyUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_tags(value):
    input = mock_input_create()
    input["tags"] = value
    with pytest.raises(ValidationError):
        StrategyCreate(**input)
        
@pytest.mark.parametrize("value", [[],["test"]])
def test_create_handles_valid_inputs_for_tags(value):
    input = mock_input_create()
    input["tags"] = value
    StrategyCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_tags(value):
    input = mock_input_update()
    input["tags"] = value
    with pytest.raises(ValidationError):
        StrategyUpdate(**input)
        
@pytest.mark.parametrize("value", [[],["test"]])
def test_update_handles_valid_inputs_for_tags(value):
    input = mock_input_update()
    input["tags"] = value
    StrategyUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_create_handles_invalid_inputs_for_template(value):
    input = mock_input_create()
    input["template"] = value
    with pytest.raises(ValidationError):
        StrategyCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_template(value):
    input = mock_input_update()
    input["template"] = value
    with pytest.raises(ValidationError):
        StrategyUpdate(**input)
    
####  Test Creation of Computed Fields  ########################################

def test_create_computes_meta():
    model = StrategyCreate.model_validate(mock_input_create(), context=mock_context())
    assert_valid_meta_for_create_request(model.meta, mock_context()["user"])

def test_update_computes_meta():
    model = StrategyUpdate.model_validate(mock_input_update(), context=mock_context())
    assert_valid_meta_for_update_request(model.meta, mock_context()["user"])

def test_create_computes_params_from_template():
    
    # "params" must have the keys extracted from "template"
    input = mock_input_create()
    model = StrategyCreate.model_validate(input, context=mock_context())
    assert sorted(model.params) == sorted([
        "text",
    ])
    
####  Test Serialization  ######################################################
    
def test_create_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_create()
    model = StrategyCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert serialized["workspace_id"] == mock_input_create()["workspace_id"]
    assert serialized["name"] == mock_input_create()["name"]
    assert serialized["tags"] == mock_input_create()["tags"]
    assert serialized["template"] == mock_input_create()["template"]
    assert sorted(serialized["params"]) == sorted([
        "text",
    ])
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_create_request(serialized.get("@meta"), mock_context()["user"])
    
def test_create_serialization_initializes_omitted_optional_inputs():
    
    # Use mock input without optional fields
    input = mock_input_create()
    input.pop("tags", None)
    model = StrategyCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that omitted optional inputs were initialized in the serialized output
    assert serialized["tags"] == []
    
    # Use mock input without optional fields
    input = mock_input_create()
    input.pop("template", None)
    model = StrategyCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that omitted optional inputs were initialized in the serialized output
    assert serialized["template"]["lang"] == "mustache"
    assert serialized["template"]["source"] == ""
    
def test_update_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_update()
    model = StrategyUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert serialized["workspace_id"] == mock_input_update()["workspace_id"]
    assert serialized["name"] == mock_input_update()["name"]
    assert serialized["tags"] == mock_input_update()["tags"]
    assert serialized["template"] == mock_input_update()["template"]
    assert serialized["params"] == sorted([
        "text",
    ])
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update_request(serialized.get("@meta"), mock_context()["user"])

def test_update_serialization_omits_omitted_optional_inputs():
    
    # Use mock input without optional fields
    input = mock_input_update()
    input.pop("name", None)
    input.pop("tags", None)
    input.pop("template", None)
    model = StrategyUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that omitted optional inputs are not in serialized output
    assert "name" not in serialized
    assert "tags" not in serialized
    assert "template" not in serialized
    assert "params" not in serialized
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update_request(serialized.get("@meta"), mock_context()["user"])