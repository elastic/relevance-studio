# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.conversations import ConversationsCreate, ConversationsUpdate
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
        "conversation_id": "conv-123",
        "title": "Chat with AI",
        "rounds": [
            {
                "id": "round-1",
                "input": {"message": "Hello, how are you?"},
                "response": {"message": "I am fine, thank you!"},
                "steps": [
                    {
                        "type": "reasoning",
                        "reasoning": "I should say hello back."
                    },
                    {
                        "type": "tool_call",
                        "tool_id": "platform.core.search",
                        "tool_call_id": "call-1",
                        "params": {"query": "weather"},
                        "results": [{"type": "success", "data": {"result": "sunny"}}]
                    }
                ],
                "model_usage": {
                    "inference_id": "test-inference-id",
                    "llm_calls": 1,
                    "input_tokens": 50,
                    "output_tokens": 20
                },
                "status": "completed",
                "started_at": "2024-02-08T12:00:00Z",
                "time_to_first_token": 100,
                "time_to_last_token": 500
            }
        ]
    }
    return input

def mock_input_update():
    """
    Returns a mock input with all required and optional fields for updates.
    """
    create_input = mock_input_create()
    return {k: v for k, v in create_input.items() if k in ["title", "rounds"]}

####  Test Validation of Input Structure  ######################################

def test_create_is_invalid_without_required_inputs():
    
    # "conversation_id" is required in the input for creates
    input = mock_input_create()
    input.pop("conversation_id", None)
    with pytest.raises(ValidationError):
        ConversationsCreate.model_validate(input, context=mock_context())

def test_create_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for creates
    input = mock_input_create()
    input["@meta"] = {"created_at": "invalid", "created_by": "should-fail"}
    with pytest.raises(ValidationError):
        ConversationsCreate.model_validate(input, context=mock_context())

def test_update_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for updates
    input = mock_input_update()
    input["@meta"] = {"updated_at": "invalid", "updated_by": "should-fail"}
    with pytest.raises(ValidationError):
        ConversationsUpdate.model_validate(input, context=mock_context())

def test_create_is_valid_without_optional_inputs():
    
    # "title" and "rounds" are optional in the input for creates
    input = {
        "conversation_id": "conv-123",
    }
    model = ConversationsCreate.model_validate(input, context=mock_context())
    
    assert model.rounds == []
    assert model.title is None

def test_create_is_invalid_with_unexpected_inputs():
    input = mock_input_create()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        ConversationsCreate.model_validate(input, context=mock_context())
        
def test_update_is_invalid_with_unexpected_inputs():
    input = mock_input_update()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        ConversationsUpdate.model_validate(input, context=mock_context())
    
def test_update_is_valid_without_optional_inputs():
    
    # "title", "rounds" are optional in the input for updates
    input = {}
    model = ConversationsUpdate.model_validate(input, context=mock_context())
    assert model.title is None
    assert model.rounds is None

####  Test Validation of Input Values  #########################################
        
@pytest.mark.parametrize("value", invalid_values_for("string", allow_null=True))
def test_create_handles_invalid_inputs_for_title(value):
    input = mock_input_create()
    input["title"] = value
    if value is not None:
        with pytest.raises(ValidationError):
            ConversationsCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string", allow_null=True))
def test_update_handles_invalid_inputs_for_title(value):
    input = mock_input_update()
    input["title"] = value
    if value is not None:
        with pytest.raises(ValidationError):
            ConversationsUpdate(**input)

def test_result_type_validation():
    input = mock_input_create()
    # "foo" is not a valid Result.type
    input["rounds"][0]["steps"][1]["results"][0]["type"] = "foo"
    with pytest.raises(ValidationError):
        ConversationsCreate.model_validate(input, context=mock_context())

    # Create a fresh copy to avoid the @meta modification from the previous call
    input = mock_input_create()
    # "data" is a valid Result.type
    input["rounds"][0]["steps"][1]["results"][0]["type"] = "data"
    ConversationsCreate.model_validate(input, context=mock_context())

####  Test Creation of Computed Fields  ########################################

def test_create_computes_meta():
    model = ConversationsCreate.model_validate(mock_input_create(), context=mock_context())
    assert_valid_meta_for_create_request(model.meta, mock_context()["user"])

def test_update_computes_meta():
    model = ConversationsUpdate.model_validate(mock_input_update(), context=mock_context())
    assert_valid_meta_for_update_request(model.meta, mock_context()["user"])
    
####  Test Serialization  ######################################################
    
def test_create_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_create()
    model = ConversationsCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    expected = mock_input_create()
    assert serialized["title"] == expected["title"]
    assert serialized["conversation_id"] == expected["conversation_id"]
    assert len(serialized["rounds"]) == len(expected["rounds"])
    assert serialized["rounds"][0]["input"]["message"] == expected["rounds"][0]["input"]["message"]
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_create_request(serialized.get("@meta"), mock_context()["user"])
    
def test_update_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_update()
    model = ConversationsUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    expected = mock_input_update()
    assert serialized["title"] == expected["title"]
    assert len(serialized["rounds"]) == len(expected["rounds"])
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update_request(serialized.get("@meta"), mock_context()["user"])

def test_update_serialization_omits_omitted_optional_inputs():
    input = {}
    model = ConversationsUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert "title" not in serialized
    assert "rounds" not in serialized
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update_request(serialized.get("@meta"), mock_context()["user"])
