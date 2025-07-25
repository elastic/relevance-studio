# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.benchmarks import BenchmarkCreate, BenchmarkUpdate
from tests.utils import (
    assert_valid_meta_for_create,
    assert_valid_meta_for_update,
    invalid_values_for,
    mock_context,
)

def mock_input_create():
    """
    Returns a mock input with all required and optional fields for creates.
    """
    input = {
        "workspace_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "name": "Product Search",
        "description": "Determine which strategy delivers the best search experience for our product catalog.",
        "tags": [
            "bm25",
            "elser",
            "signals"
        ],
        "task": {
            "metrics": [
                "ndcg",
                "precision",
                "recall"
            ],
            "k": 10,
            "strategies": {
                "_ids": [
                    "cd8e7636-8217-4d7b-9828-49a2e36fc12d",
                    "926ff022-e417-482d-851c-4d09da44f1d1",
                ],
                "tags": [
                    "bm25",
                    "elser",
                    "signals"
                ]
            },
            "scenarios": {
                "_ids": [
                    "f4009386-aa2d-4c84-8f1c-b9dea81489d1",
                    "8dbbb8b8-d190-434d-b65a-6206ded14a2d",
                ],
                "tags": [
                    "head",
                    "body",
                    "tail",
                ],
                "sample_seed": "test",
                "sample_size": 5000
            }
        }
    }
    return input

def mock_input_update():
    """
    Returns a mock input with all required and optional fields for updates.
    """
    input = mock_input_create()
    input["task"].pop("k")
    return input

####  Test Validation of Input Structure  ######################################

def test_create_is_invalid_without_required_inputs():
    
    # "workspace_id" is required in the input for creates
    input = mock_input_create()
    input.pop("workspace_id", None)
    with pytest.raises(ValidationError):
        BenchmarkCreate.model_validate(input, context=mock_context())
    
    # "name" is required in the input for creates
    input = mock_input_create()
    input.pop("name", None)
    with pytest.raises(ValidationError):
        BenchmarkCreate.model_validate(input, context=mock_context())

def test_update_is_invalid_without_required_inputs():
    
    # "workspace_id" is required in the input for updates
    input = mock_input_create()
    input.pop("workspace_id", None)
    with pytest.raises(ValidationError):
        BenchmarkUpdate.model_validate(input, context=mock_context())

def test_create_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for creates
    input = mock_input_create()
    input["@meta"] = {"created_at": "invalid", "created_by": "should-fail"}
    with pytest.raises(ValidationError):
        BenchmarkCreate.model_validate(input, context=mock_context())

def test_update_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for updates
    input = mock_input_update()
    input["@meta"] = {"updated_at": "invalid", "updated_by": "should-fail"}
    with pytest.raises(ValidationError):
        BenchmarkUpdate.model_validate(input, context=mock_context())
    
    # "task.metrics.k" is forbidden in the input for updates
    input = mock_input_update()
    input["task"]["k"] = 5
    with pytest.raises(ValidationError):
        BenchmarkUpdate.model_validate(input, context=mock_context())

def test_create_is_valid_without_optional_inputs():
    
    # "description" is optional in the input for creates
    input = mock_input_create()
    input.pop("description", None)
    input.pop("tags", None)
    model = BenchmarkCreate.model_validate(input, context=mock_context())
    
    # creates must initialize optional fields that were omitted in the input
    assert model.tags == []
    
    # "task" is optional in the input for creates
    input = mock_input_create()
    input["task"].pop("metrics", None)
    model = BenchmarkCreate.model_validate(input, context=mock_context())
    assert sorted(model.task.metrics) == sorted([
        "ndcg", "precision", "recall"
    ])
    
def test_create_is_invalid_with_unexpected_inputs():
    input = mock_input_create()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        BenchmarkCreate.model_validate(input, context=mock_context())
        
def test_update_is_invalid_with_unexpected_inputs():
    input = mock_input_update()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        BenchmarkUpdate.model_validate(input, context=mock_context())
    
def test_update_is_valid_without_optional_inputs():
    
    # "name" is optional in the input for updates
    input = mock_input_update()
    input.pop("name", None)
    model = BenchmarkUpdate.model_validate(input, context=mock_context())
    assert model.name is None
    
    # "description" is optional in the input for updates
    input = mock_input_update()
    input.pop("description", None)
    model = BenchmarkUpdate.model_validate(input, context=mock_context())
    assert model.description is None
    
####  Test Validation of Input Values  #########################################
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_workspace_id(value):
    input = mock_input_create()
    input["workspace_id"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_workspace_id(value):
    input = mock_input_update()
    input["workspace_id"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_name(value):
    input = mock_input_create()
    input["name"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_name(value):
    input = mock_input_update()
    input["name"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string", allow_empty=True))
def test_update_handles_invalid_inputs_for_description(value):
    input = mock_input_update()
    input["description"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_tags(value):
    input = mock_input_create()
    input["tags"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", [[],["test"]])
def test_create_handles_valid_inputs_for_tags(value):
    input = mock_input_create()
    input["tags"] = value
    BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_tags(value):
    input = mock_input_update()
    input["tags"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", [[],["test"]])
def test_update_handles_valid_inputs_for_tags(value):
    input = mock_input_update()
    input["tags"] = value
    BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_metrics(value):
    input = mock_input_create()
    input["task"]["metrics"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_task_metrics(value):
    input = mock_input_update()
    input["task"]["metrics"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_1"))
def test_create_handles_invalid_inputs_for_task_k(value):
    input = mock_input_create()
    input["task"]["k"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_1"))
def test_update_handles_invalid_inputs_for_task_k(value):
    input = mock_input_update()
    input["task"]["k"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_strategies_ids(value):
    input = mock_input_create()
    input["task"]["strategies"]["_ids"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_create_handles_valid_inputs_for_task_strategies_ids(value):
    input = mock_input_create()
    input["task"]["strategies"]["_ids"] = value
    BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_task_strategies_ids(value):
    input = mock_input_update()
    input["task"]["strategies"]["_ids"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_update_handles_valid_inputs_for_task_strategies_ids(value):
    input = mock_input_update()
    input["task"]["strategies"]["_ids"] = value
    BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_strategies_tags(value):
    input = mock_input_create()
    input["task"]["strategies"]["tags"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_create_handles_valid_inputs_for_task_strategies_tags(value):
    input = mock_input_create()
    input["task"]["strategies"]["tags"] = value
    BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_task_strategies_tags(value):
    input = mock_input_update()
    input["task"]["strategies"]["tags"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_update_handles_valid_inputs_for_task_strategies_tags(value):
    input = mock_input_update()
    input["task"]["strategies"]["tags"] = value
    BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_scenarios_ids(value):
    input = mock_input_create()
    input["task"]["scenarios"]["_ids"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_create_handles_valid_inputs_for_task_scenarios_ids(value):
    input = mock_input_create()
    input["task"]["scenarios"]["_ids"] = value
    BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_task_scenarios_ids(value):
    input = mock_input_update()
    input["task"]["scenarios"]["_ids"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_update_handles_valid_inputs_for_task_scenarios_ids(value):
    input = mock_input_update()
    input["task"]["scenarios"]["_ids"] = value
    BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_scenarios_tags(value):
    input = mock_input_create()
    input["task"]["scenarios"]["tags"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_create_handles_valid_inputs_for_task_scenarios_tags(value):
    input = mock_input_create()
    input["task"]["scenarios"]["tags"] = value
    BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_task_scenarios_tags(value):
    input = mock_input_update()
    input["task"]["scenarios"]["tags"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_update_handles_valid_inputs_for_task_scenarios_tags(value):
    input = mock_input_update()
    input["task"]["scenarios"]["tags"] = value
    BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_0"))
def test_create_handles_invalid_inputs_for_task_scenarios_sample_size(value):
    input = mock_input_create()
    input["task"]["scenarios"]["sample_size"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_0"))
def test_update_handles_invalid_inputs_for_task_scenarios_sample_size(value):
    input = mock_input_update()
    input["task"]["scenarios"]["sample_size"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string", allow_empty=True, allow_null=True))
def test_create_handles_invalid_inputs_for_task_scenarios_sample_seed(value):
    input = mock_input_create()
    input["task"]["scenarios"]["sample_seed"] = value
    with pytest.raises(ValidationError):
        BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", [None, "test" ])
def test_create_handles_valid_inputs_for_task_scenarios_sample_seed(value):
    input = mock_input_create()
    input["task"]["scenarios"]["sample_seed"] = value
    BenchmarkCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string", allow_empty=True, allow_null=True))
def test_update_handles_invalid_inputs_for_task_scenarios_sample_seed(value):
    input = mock_input_update()
    input["task"]["scenarios"]["sample_seed"] = value
    with pytest.raises(ValidationError):
        BenchmarkUpdate(**input)
        
@pytest.mark.parametrize("value", [None, "test" ])
def test_update_handles_valid_inputs_for_task_scenarios_sample_seed(value):
    input = mock_input_update()
    input["task"]["scenarios"]["sample_seed"] = value
    BenchmarkUpdate(**input)
    
####  Test Creation of Computed Fields  ########################################

def test_create_computes_meta():
    model = BenchmarkCreate.model_validate(mock_input_create(), context=mock_context())
    assert_valid_meta_for_create(model.meta, mock_context()["user"])

def test_update_computes_meta():
    model = BenchmarkUpdate.model_validate(mock_input_update(), context=mock_context())
    assert_valid_meta_for_update(model.meta, mock_context()["user"])
    
####  Test Serialization  ######################################################
    
def test_create_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_create()
    model = BenchmarkCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    expected = mock_input_create()
    assert serialized["workspace_id"] == expected["workspace_id"]
    assert serialized["name"] == expected["name"]
    assert serialized["description"] == expected["description"]
    assert sorted(serialized["tags"]) == sorted(expected["tags"])
    assert sorted(serialized["task"]["metrics"]) == sorted(expected["task"]["metrics"])
    assert serialized["task"]["k"] == expected["task"]["k"]
    assert sorted(serialized["task"]["strategies"]["_ids"]) == sorted(expected["task"]["strategies"]["_ids"])
    assert sorted(serialized["task"]["strategies"]["tags"]) == sorted(expected["task"]["strategies"]["tags"])
    assert sorted(serialized["task"]["scenarios"]["_ids"]) == sorted(expected["task"]["scenarios"]["_ids"])
    assert sorted(serialized["task"]["scenarios"]["tags"]) == sorted(expected["task"]["scenarios"]["tags"])
    assert serialized["task"]["scenarios"]["sample_size"] == expected["task"]["scenarios"]["sample_size"]
    assert serialized["task"]["scenarios"]["sample_seed"] == expected["task"]["scenarios"]["sample_seed"]
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_create(serialized.get("@meta"), mock_context()["user"])
    
def test_create_serialization_initializes_omitted_optional_inputs():
    
    # Use mock input without optional fields
    input = mock_input_create()
    input.pop("description", None)
    input.pop("tags", None)
    input.pop("task", None)
    model = BenchmarkCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that omitted optional inputs were initialized in the serialized output
    expected = mock_input_create()
    assert serialized["description"] is None
    assert serialized["tags"] == []
    assert sorted(serialized["task"]["metrics"]) == sorted(expected["task"]["metrics"])
    assert serialized["task"]["k"] == expected["task"]["k"]
    assert sorted(serialized["task"]["strategies"]["_ids"]) == []
    assert sorted(serialized["task"]["strategies"]["tags"]) == []
    assert sorted(serialized["task"]["scenarios"]["_ids"]) == []
    assert sorted(serialized["task"]["scenarios"]["tags"]) == []
    assert serialized["task"]["scenarios"]["sample_size"] == 1000
    assert serialized["task"]["scenarios"]["sample_seed"] == None
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_create(serialized.get("@meta"), mock_context()["user"])
    
def test_update_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_update()
    model = BenchmarkUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    expected = mock_input_update()
    assert serialized["workspace_id"] == expected["workspace_id"]
    assert serialized["name"] == expected["name"]
    assert serialized["description"] == expected["description"]
    assert sorted(serialized["tags"]) == sorted(expected["tags"])
    assert sorted(serialized["task"]["metrics"]) == sorted(expected["task"]["metrics"])
    assert "k" not in serialized["task"]
    assert sorted(serialized["task"]["strategies"]["_ids"]) == sorted(expected["task"]["strategies"]["_ids"])
    assert sorted(serialized["task"]["strategies"]["tags"]) == sorted(expected["task"]["strategies"]["tags"])
    assert sorted(serialized["task"]["scenarios"]["_ids"]) == sorted(expected["task"]["scenarios"]["_ids"])
    assert sorted(serialized["task"]["scenarios"]["tags"]) == sorted(expected["task"]["scenarios"]["tags"])
    assert serialized["task"]["scenarios"]["sample_size"] == expected["task"]["scenarios"]["sample_size"]
    assert serialized["task"]["scenarios"]["sample_seed"] == expected["task"]["scenarios"]["sample_seed"]
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update(serialized.get("@meta"), mock_context()["user"])

def test_update_serialization_omits_omitted_optional_inputs():
    input = mock_input_update()
    input.pop("name", None)
    input.pop("description", None)
    input.pop("task", None)
    model = BenchmarkUpdate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    assert "name" not in serialized
    assert "description" not in serialized
    assert "task" not in serialized
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_update(serialized.get("@meta"), mock_context()["user"])