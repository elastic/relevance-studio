# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.judgements import JudgementCreate
from tests.utils import (
    assert_valid_meta_for_create,
    invalid_values_for,
    mock_context,
)

def mock_input_create():
    """
    Returns a mock input with all required and optional fields for creates.
    """
    input = {
        "workspace_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "scenario_id": "5199e0ae-de59-5227-9647-c44f2c6617fc",
        "index": "products",
        "doc_id": "41476",
        "rating": 3
    }
    return input

####  Test Validation of Input Structure  ######################################

def test_create_is_invalid_without_required_inputs():
    
    # "workspace_id" is required in the input for creates
    input = mock_input_create()
    input.pop("workspace_id", None)
    with pytest.raises(ValidationError):
        JudgementCreate.model_validate(input, context=mock_context())
    
    # "scenario_id" is required in the input for creates
    input = mock_input_create()
    input.pop("scenario_id", None)
    with pytest.raises(ValidationError):
        JudgementCreate.model_validate(input, context=mock_context())
    
    # "index" is required in the input for creates
    input = mock_input_create()
    input.pop("index", None)
    with pytest.raises(ValidationError):
        JudgementCreate.model_validate(input, context=mock_context())
    
    # "doc_id" is required in the input for creates
    input = mock_input_create()
    input.pop("doc_id", None)
    with pytest.raises(ValidationError):
        JudgementCreate.model_validate(input, context=mock_context())
    
    # "rating" is required in the input for creates
    input = mock_input_create()
    input.pop("rating", None)
    with pytest.raises(ValidationError):
        JudgementCreate.model_validate(input, context=mock_context())

def test_create_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for creates
    input = mock_input_create()
    input["@meta"] = {"created_at": "invalid", "created_by": "should-fail"}
    with pytest.raises(ValidationError):
        JudgementCreate.model_validate(input, context=mock_context())

def test_create_is_valid_without_optional_inputs():
    
    # judgement creates have no optional inputs
    pass
    
def test_create_is_invalid_with_unexpected_inputs():
    input = mock_input_create()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        JudgementCreate.model_validate(input, context=mock_context())
    
####  Test Validation of Input Values  #########################################
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_workspace_id(value):
    input = mock_input_create()
    input["workspace_id"] = value
    with pytest.raises(ValidationError):
        JudgementCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_scenario_id(value):
    input = mock_input_create()
    input["scenario_id"] = value
    with pytest.raises(ValidationError):
        JudgementCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_index(value):
    input = mock_input_create()
    input["index"] = value
    with pytest.raises(ValidationError):
        JudgementCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_doc_id(value):
    input = mock_input_create()
    input["doc_id"] = value
    with pytest.raises(ValidationError):
        JudgementCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_0"))
def test_create_handles_invalid_inputs_for_rating(value):
    input = mock_input_create()
    input["rating"] = value
    with pytest.raises(ValidationError):
        JudgementCreate(**input)
    
####  Test Creation of Computed Fields  ########################################

def test_create_computes_meta():
    model = JudgementCreate.model_validate(mock_input_create(), context=mock_context())
    assert_valid_meta_for_create(model.meta, mock_context()["user"])
    
####  Test Serialization  ######################################################
    
def test_create_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_create()
    model = JudgementCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert serialized["workspace_id"] == mock_input_create()["workspace_id"]
    assert serialized["scenario_id"] == mock_input_create()["scenario_id"]
    assert serialized["index"] == mock_input_create()["index"]
    assert serialized["doc_id"] == mock_input_create()["doc_id"]
    assert serialized["rating"] == mock_input_create()["rating"]
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_create(serialized.get("@meta"), mock_context()["user"])