# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.evaluations import (
    EvaluationCreate,
    EvaluationSkip,
    EvaluationFail,
    EvaluationComplete,
)
from tests.utils import mock_context, invalid_values_for

def assert_valid_meta_for_create(meta, created_by: str = "unknown"):
    assert meta is not None
    assert meta.get("status") == "pending"
    assert meta.get("created_at") is not None
    assert meta.get("created_by") == created_by
    assert "started_at" in meta
    assert meta["started_at"] is None
    assert "started_by" in meta
    assert meta["started_by"] is None
    assert "stopped_at" in meta
    assert meta["stopped_at"] is None
    
def assert_valid_meta_for_skip(meta):
    assert meta is not None
    assert meta.get("status") == "skipped"
    assert meta.get("stopped_at") is not None

def assert_valid_meta_for_fail(meta):
    assert meta is not None
    assert meta.get("status") == "failed"
    assert meta.get("stopped_at") is not None

def assert_valid_meta_for_complete(meta):
    assert meta is not None
    assert meta.get("status") == "completed"
    assert meta.get("stopped_at") is not None

def mock_input_create():
    """
    Returns a mock input with all required and optional fields for creates.
    """
    input = {
        "workspace_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "benchmark_id": "49d68c9a-35ed-4558-a98b-96c04ccb540c",
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
    For brevity, the summary, results, runtime, and unrated_docs fields only
    have a single example each for the purpose of model validation. They don't
    align with the inputs of strategy_id and scenario_id.
    """
    input = {
        "strategy_id": [
            "cd8e7636-8217-4d7b-9828-49a2e36fc12d",
            "926ff022-e417-482d-851c-4d09da44f1d1",
        ],
        "scenario_id": [
            "f4009386-aa2d-4c84-8f1c-b9dea81489d1",
            "8dbbb8b8-d190-434d-b65a-6206ded14a2d",
        ],
        "summary": {},
        "results": [
            {
                "searches": [
                    {
                        "hits": [
                            {
                                "hit": {
                                    "_index": "test",
                                    "_id": "doc_1",
                                    "_score": 3.14,
                                },
                                "rating": 4,
                            }
                        ],
                        "metrics": {
                            "ndcg": 0.7,
                            "precision": 0.8,
                            "recall": 0.6,
                        },
                        "scenario_id": "f4009386-aa2d-4c84-8f1c-b9dea81489d1"
                    },
                ],
                "strategy_id": "cd8e7636-8217-4d7b-9828-49a2e36fc12d"
            }
        ],
        "runtime": {
            "indices": {
                "products": {
                    "_fingerprint": "93d275fc8480680bc4c7d00fd0ec91ab",
                    "_index": "products",
                    "aliases": {},
                    "mappings": {},
                    "settings": {},
                    "shards": [],
                },
            },
            "scenarios": {
                "c20dccc3-1a8d-581f-a026-bfbecf094b32": {
                    "_fingerprint": "1bb2822ed6817f2ff209c804db7edbad",
                    "name": "green leather handbags",
                    "values": {
                        "text": "green leather handbags",
                    },
                    "params": [
                        "text",
                    ],
                    "tags": [
                        "body",
                    ],
                },
            },
            "judgements": {
                "f9952b05-ed76-5984-a54a-915058eecbeb": {
                    "_fingerprint": "f3d4a454a85a82bc12f6cba839fd2d05",
                    "@meta": {
                        "created_at": "2025-06-10T00:00:22.000000Z",
                        "created_by": "unknown",
                        "updated_at": None,
                        "updated_by": None
                    },
                    "scenario_id": "cde7578a-70fd-5434-a417-0673a25a5c9f",
                    "index": "products",
                    "doc_id": "35478",
                    "rating": 3,
                },
            },
            "strategies": {
                "c6057064-7d67-5855-8c24-8d312c6b4cf0": {
                    "_fingerprint": "832a25c4e8c54b9ff8a2e39ed3ae629a",
                    "name": "Classical - Multifield match w/ boosts",
                    "tags": [
                        "bm25",
                    ],
                    "params": [
                        "text",
                    ],
                    "template": {
                        "lang": "mustache",
                        "source": """{"query":{"query_string":{"query":"{{text}}"}}}"""
                    },
                }
            },
        },
        "unrated_docs": [
            {
                "_index": "products",
                "_id": "doc_2",
                "count": 2,
                "strategies": [
                    "cd8e7636-8217-4d7b-9828-49a2e36fc12d",
                ],
                "scenarios": [
                    "f4009386-aa2d-4c84-8f1c-b9dea81489d1",
                ],
            },
        ],
        "error": {},
        "took": 4096
    }
    return input

####  Test Validation of Input Structure  ######################################

def test_create_is_invalid_without_required_inputs():
    
    # "workspace_id" is required in the input for creates
    input = mock_input_create()
    input.pop("workspace_id", None)
    with pytest.raises(ValidationError):
        EvaluationCreate.model_validate(input, context=mock_context())
    
    # "benchmark_id" is required in the input for creates
    input = mock_input_create()
    input.pop("benchmark_id", None)
    with pytest.raises(ValidationError):
        EvaluationCreate.model_validate(input, context=mock_context())
        
    # "task" is optional in the input for creates
    input = mock_input_create()
    input.pop("task", None)
    with pytest.raises(ValidationError):
        EvaluationCreate.model_validate(input, context=mock_context())

def test_create_is_invalid_with_forbidden_inputs():
    
    # "@meta" is forbidden in the input for creates
    input = mock_input_create()
    input["@meta"] = {"created_at": "invalid", "created_by": "should-fail"}
    with pytest.raises(ValidationError):
        EvaluationCreate.model_validate(input, context=mock_context())
        
def test_update_is_invalid_with_forbidden_inputs():
    input = mock_input_update()
    input["@meta"] = {"created_at": "invalid", "created_by": "should-fail"}
    with pytest.raises(ValidationError):
        EvaluationComplete.model_validate(input, context=mock_context())
    with pytest.raises(ValidationError):
        EvaluationFail.model_validate(input, context=mock_context())
    with pytest.raises(ValidationError):
        EvaluationSkip.model_validate(input, context=mock_context())
    
def test_create_is_invalid_with_unexpected_inputs():
    input = mock_input_create()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        EvaluationCreate.model_validate(input, context=mock_context())
        
def test_update_is_invalid_with_unexpected_inputs():
    input = mock_input_update()
    input["foo"] = "bar"
    with pytest.raises(ValidationError):
        EvaluationComplete.model_validate(input, context=mock_context())
    with pytest.raises(ValidationError):
        EvaluationFail.model_validate(input, context=mock_context())
    with pytest.raises(ValidationError):
        EvaluationSkip.model_validate(input, context=mock_context())
    
####  Test Validation of Input Values  #########################################
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_workspace_id(value):
    input = mock_input_create()
    input["workspace_id"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_create_handles_invalid_inputs_for_benchmark_id(value):
    input = mock_input_create()
    input["benchmark_id"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings"))
def test_create_handles_invalid_inputs_for_task_metrics(value):
    input = mock_input_create()
    input["task"]["metrics"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_1"))
def test_create_handles_invalid_inputs_for_task_k(value):
    input = mock_input_create()
    input["task"]["k"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_strategies_ids(value):
    input = mock_input_create()
    input["task"]["strategies"]["_ids"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_create_handles_valid_inputs_for_task_strategies_ids(value):
    input = mock_input_create()
    input["task"]["strategies"]["_ids"] = value
    EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_strategies_tags(value):
    input = mock_input_create()
    input["task"]["strategies"]["tags"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_create_handles_valid_inputs_for_task_strategies_tags(value):
    input = mock_input_create()
    input["task"]["strategies"]["tags"] = value
    EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_scenarios_ids(value):
    input = mock_input_create()
    input["task"]["scenarios"]["_ids"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_create_handles_valid_inputs_for_task_scenarios_ids(value):
    input = mock_input_create()
    input["task"]["scenarios"]["_ids"] = value
    EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_create_handles_invalid_inputs_for_task_scenarios_tags(value):
    input = mock_input_create()
    input["task"]["scenarios"]["tags"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", [[], ["test"]])
def test_create_handles_valid_inputs_for_task_scenarios_tags(value):
    input = mock_input_create()
    input["task"]["scenarios"]["tags"] = value
    EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_1"))
def test_create_handles_invalid_inputs_for_task_scenarios_sample_size(value):
    input = mock_input_create()
    input["task"]["scenarios"]["sample_size"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string", allow_empty=True, allow_null=True))
def test_create_handles_invalid_inputs_for_task_scenarios_sample_seed(value):
    input = mock_input_create()
    input["task"]["scenarios"]["sample_seed"] = value
    with pytest.raises(ValidationError):
        EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", [None, "test" ])
def test_create_handles_valid_inputs_for_task_scenarios_sample_seed(value):
    input = mock_input_create()
    input["task"]["scenarios"]["sample_seed"] = value
    EvaluationCreate(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_scenario_id(value):
    input = mock_input_update()
    input["scenario_id"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_strategy_id(value):
    input = mock_input_update()
    input["strategy_id"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_summary(value):
    input = mock_input_update()
    input["summary"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_objects", allow_empty=True))
def test_update_handles_invalid_inputs_for_results(value):
    input = mock_input_update()
    input["results"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_objects", allow_empty=True))
def test_update_handles_invalid_inputs_for_results_searches(value):
    input = mock_input_update()
    input["results"][0]["searches"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_results_strategy_id(value):
    input = mock_input_update()
    input["results"][0]["strategy_id"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_objects", allow_empty=True))
def test_update_handles_invalid_inputs_for_results_searches(value):
    input = mock_input_update()
    input["results"][0]["searches"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_objects", allow_empty=True))
def test_update_handles_invalid_inputs_for_results_searches_hits(value):
    input = mock_input_update()
    input["results"][0]["searches"][0]["hits"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object"))
def test_update_handles_invalid_inputs_for_results_searches_hits_hit(value):
    input = mock_input_update()
    input["results"][0]["searches"][0]["hits"][0]["hit"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_results_searches_hits_hit_id(value):
    input = mock_input_update()
    input["results"][0]["searches"][0]["hits"][0]["hit"]["_id"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_results_searches_hits_hit_index(value):
    input = mock_input_update()
    input["results"][0]["searches"][0]["hits"][0]["hit"]["_index"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("number", allow_null=True))
def test_update_handles_invalid_inputs_for_results_searches_hits_hit_score(value):
    input = mock_input_update()
    input["results"][0]["searches"][0]["hits"][0]["hit"]["_score"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_0", allow_null=True))
def test_update_handles_invalid_inputs_for_results_searches_hits_hit_rating(value):
    input = mock_input_update()
    input["results"][0]["searches"][0]["hits"][0]["rating"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_results_searches_metrics(value):
    input = mock_input_update()
    input["results"][0]["searches"][0]["metrics"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("number", allow_null=True))
def test_update_handles_invalid_inputs_for_results_searches_metric_value(value):
    input = mock_input_update()
    for metric in [ "ndcg", "precision", "recall" ]:
        input["results"][0]["searches"][0]["metrics"][metric] = value
        with pytest.raises(ValidationError):
            EvaluationComplete(**input)
        with pytest.raises(ValidationError):
            EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_results_searches_scenario_id(value):
    input = mock_input_update()
    input["results"][0]["searches"][0]["scenario_id"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_runtime(value):
    input = mock_input_update()
    input["runtime"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_runtime_indices(value):
    input = mock_input_update()
    input["runtime"]["indices"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_runtime_scenarios(value):
    input = mock_input_update()
    input["runtime"]["scenarios"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_runtime_judgements(value):
    input = mock_input_update()
    input["runtime"]["judgements"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_runtime_strategies(value):
    input = mock_input_update()
    input["runtime"]["strategies"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_objects", allow_empty=True))
def test_update_handles_invalid_inputs_for_unrated_docs(value):
    input = mock_input_update()
    input["unrated_docs"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_unrated_docs_index(value):
    input = mock_input_update()
    input["unrated_docs"][0]["_index"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("string"))
def test_update_handles_invalid_inputs_for_unrated_docs_id(value):
    input = mock_input_update()
    input["unrated_docs"][0]["_id"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_0"))
def test_update_handles_invalid_inputs_for_unrated_docs_count(value):
    input = mock_input_update()
    input["unrated_docs"][0]["count"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_unrated_docs_strategies(value):
    input = mock_input_update()
    input["unrated_docs"][0]["strategies"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("list_of_strings", allow_empty=True))
def test_update_handles_invalid_inputs_for_unrated_docs_scenarios(value):
    input = mock_input_update()
    input["unrated_docs"][0]["scenarios"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("object", allow_empty=True))
def test_update_handles_invalid_inputs_for_error(value):
    input = mock_input_update()
    input["error"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
        
@pytest.mark.parametrize("value", invalid_values_for("int_ge_0"))
def test_update_handles_invalid_inputs_for_took(value):
    input = mock_input_update()
    input["took"] = value
    with pytest.raises(ValidationError):
        EvaluationComplete(**input)
    with pytest.raises(ValidationError):
        EvaluationFail(**input)
    with pytest.raises(ValidationError):
        EvaluationSkip(**input)
    
####  Test Creation of Computed Fields  ########################################

def test_create_computes_meta():
    model = EvaluationCreate.model_validate(mock_input_create(), context=mock_context())
    assert_valid_meta_for_create(model.meta, mock_context()["user"])

def test_skip_computes_meta():
    model = EvaluationSkip.model_validate({}, context=mock_context())
    assert_valid_meta_for_skip(model.meta)

def test_complete_computes_meta():
    model = EvaluationComplete.model_validate(mock_input_update(), context=mock_context())
    assert_valid_meta_for_complete(model.meta)
    
def test_fail_computes_meta():
    model = EvaluationFail.model_validate(mock_input_update(), context=mock_context())
    assert_valid_meta_for_fail(model.meta)
    
####  Test Serialization  ######################################################
    
def test_create_serialization_has_all_given_inputs():
    
    # Use mock input with required and optional fields
    input = mock_input_create()
    model = EvaluationCreate.model_validate(input, context=mock_context())
    serialized = model.serialize()
    
    # Test that inputs are in serialized output
    expected = mock_input_create()
    assert serialized["workspace_id"] == expected["workspace_id"]
    assert serialized["benchmark_id"] == expected["benchmark_id"]
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
    
def test_skip_serialization():
    
    # Use mock input with required and optional fields
    model = EvaluationSkip.model_validate({}, context=mock_context())
    serialized = model.serialize()
    
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_skip(serialized.get("@meta"))
    
def test_complete_serialization():
    
    # Use mock input with required and optional fields
    model = EvaluationComplete.model_validate(mock_input_update(), context=mock_context())
    serialized = model.serialize()
    expected = mock_input_update()
    assert sorted(serialized["strategy_id"]) == sorted(expected["strategy_id"])
    assert sorted(serialized["scenario_id"]) == sorted(expected["scenario_id"])
    assert serialized["summary"] == expected["summary"]
    assert serialized["results"] == expected["results"]
    assert serialized["runtime"] == expected["runtime"]
    assert serialized["unrated_docs"] == expected["unrated_docs"]
    assert serialized["took"] == expected["took"]
        
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_complete(serialized.get("@meta"))
    
def test_fail_serialization():
    
    # Use mock input with required and optional fields
    model = EvaluationFail.model_validate(mock_input_update(), context=mock_context())
    serialized = model.serialize()
    expected = mock_input_update()
    assert sorted(serialized["strategy_id"]) == sorted(expected["strategy_id"])
    assert sorted(serialized["scenario_id"]) == sorted(expected["scenario_id"])
    assert serialized["summary"] == expected["summary"]
    assert serialized["results"] == expected["results"]
    assert serialized["runtime"] == expected["runtime"]
    assert serialized["unrated_docs"] == expected["unrated_docs"]
    assert serialized["took"] == expected["took"]
        
    # Test that @meta fields were properly serialized
    assert "@meta" in serialized and "meta" not in serialized
    assert_valid_meta_for_fail(serialized.get("@meta"))