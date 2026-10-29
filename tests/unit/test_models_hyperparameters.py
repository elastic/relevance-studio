# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server import utils
from server.models.benchmarks import BenchmarkCreate, BenchmarkUpdate, TaskCreate
from server.models.hyperparameters import Hyperparameter, Optimization
from server.models.scenarios import ScenarioCreate
from server.models.strategies import StrategyCreate, StrategyUpdate
from tests.utils import mock_context

WS = "58278355-f4f3-56d2-aa81-498250f27798"
SOURCE = '{"query":{"match":{"name":{"query":"{{ text }}","boost":{{hp.name_boost}}}}}}'


def strategy_input(**overrides):
    doc = {
        "workspace_id": WS,
        "name": "Boosted",
        "template": { "lang": "mustache", "source": SOURCE },
        "hyperparameters": [{
            "name": "name_boost", "type": "number", "promoted_value": 2.0,
            "testable_values": { "type": "range", "min": 0 },
        }],
    }
    doc.update(overrides)
    return doc


####  Template helpers  ########################################################

def test_extract_params_excludes_hyperparameters():
    assert utils.extract_params(SOURCE) == ["text"]


def test_extract_hyperparameter_refs_finds_simple_and_tojson_refs():
    source = '{"a":{{hp.one}},"b":"{{ hp.two }}","c":{{#toJson}}hp.three{{/toJson}},"d":"{{text}}"}'
    assert utils.extract_hyperparameter_refs(source) == ["one", "three", "two"]


def test_render_hyperparameters_renders_types_and_preserves_scenario_vars():
    source = '{"q":"{{text}}","n":{{hp.n}},"f":{{hp.f}},"b":{{hp.b}},"s":"{{hp.s}}","{{hp.key}}":1}'
    out = utils.render_hyperparameters(source, {
        "n": 3, "f": 0.5, "b": True, "s": "a b", "key": "name.text",
    })
    assert out == '{"q":"{{text}}","n":3,"f":0.5,"b":true,"s":"a b","name.text":1}'
    assert isinstance(__import__("json").loads(out.replace("{{text}}", "x")), dict)


def test_render_hyperparameters_tojson_and_escaping():
    out = utils.render_hyperparameters(
        '{"v":{{#toJson}}hp.s{{/toJson}},"w":"{{hp.s}}"}', { "s": 'a"b' },
    )
    assert out == '{"v":"a\\"b","w":"a\\"b"}'


def test_render_hyperparameters_missing_value_raises():
    with pytest.raises(KeyError):
        utils.render_hyperparameters("{{hp.x}}", {})


def test_normalize_hyperparameter_value():
    assert utils.normalize_hyperparameter_value("number", 0.1 + 0.2) == 0.3
    assert utils.normalize_hyperparameter_value("number", 2.0) == 2
    assert isinstance(utils.normalize_hyperparameter_value("number", 2.0), int)
    assert utils.normalize_hyperparameter_value("number", 2) == 2
    assert utils.normalize_hyperparameter_value("boolean", 1) is True
    assert utils.normalize_hyperparameter_value("string", "x") == "x"


####  Strategies  ##############################################################

def test_strategy_with_hyperparameters_is_valid_and_computes_fields():
    doc = StrategyCreate.model_validate(strategy_input(), context=mock_context()).serialize()
    assert doc["params"] == ["text"]
    assert doc["hyperparameter_refs"] == ["name_boost"]
    assert doc["hyperparameters"][0]["testable_values"] == { "type": "range", "min": 0 }
    assert doc["hyperparameters"][0]["promoted_value"] == 2.0
    assert "max" not in doc["hyperparameters"][0]["testable_values"]  # None values are dropped


def test_strategy_without_hyperparameters_still_valid():
    doc = StrategyCreate.model_validate(
        strategy_input(hyperparameters=[], template={ "lang": "mustache", "source": '{"q":"{{text}}"}' }),
        context=mock_context(),
    ).serialize()
    assert doc["hyperparameters"] == [] and doc["hyperparameter_refs"] == []


def test_strategy_rejects_undefined_template_reference():
    with pytest.raises(ValidationError, match="undefined hyperparameters"):
        StrategyCreate.model_validate(strategy_input(hyperparameters=[]), context=mock_context())


RANGE = { "type": "range", "min": 0, "max": 5 }
SET_NUMBERS = { "type": "set", "values": [1, 2, 3] }


@pytest.mark.parametrize("hp", [
    { "name": "bad name", "type": "number", "promoted_value": 1, "testable_values": RANGE },
    { "name": "n", "type": "integer", "promoted_value": 1, "testable_values": RANGE },
    { "name": "n", "type": "float", "promoted_value": 1, "testable_values": RANGE },
    { "name": "n", "type": "number", "promoted_value": True, "testable_values": RANGE },
    { "name": "s", "type": "string", "promoted_value": 'a"b', "testable_values": { "type": "set", "values": ['a"b', "c"] }},
    { "name": "b", "type": "boolean", "promoted_value": "yes" },
    { "name": "x", "type": "unknown", "promoted_value": 1, "testable_values": RANGE },
    # Testable values are required for numbers and strings
    { "name": "n", "type": "number", "promoted_value": 1 },
    { "name": "s", "type": "string", "promoted_value": "a" },
    # A range is only for numbers
    { "name": "s", "type": "string", "promoted_value": "a", "testable_values": RANGE },
    # A set needs two distinct values of the hyperparameter's type
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": { "type": "set", "values": [1] }},
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": { "type": "set", "values": [1, 1.0] }},
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": { "type": "set", "values": [] }},
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": { "type": "set", "values": [1, "a"] }},
    { "name": "s", "type": "string", "promoted_value": "a", "testable_values": { "type": "set", "values": ["a", 'x"y'] }},
    # A range needs min < max when both are given
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": { "type": "range", "min": 5, "max": 1 }},
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": { "type": "range", "min": 1, "max": 1 }},
    # Step, count, and log are for benchmarks
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": { "type": "range", "min": 0, "max": 5, "step": 1 }},
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": { "type": "range", "min": 0, "max": 5, "log": True }},
    # The promoted value must be one of the testable values
    { "name": "n", "type": "number", "promoted_value": 6, "testable_values": RANGE },
    { "name": "n", "type": "number", "promoted_value": -1, "testable_values": { "type": "range", "min": 0 }},
    { "name": "n", "type": "number", "promoted_value": 9, "testable_values": SET_NUMBERS },
    # A boolean always has the testable values true and false
    { "name": "b", "type": "boolean", "promoted_value": True, "testable_values": { "type": "set", "values": [True, True] }},
    # The old names are gone
    { "name": "n", "type": "number", "default": 1, "testable_values": RANGE },
    { "name": "n", "type": "number", "promoted_value": 1, "search_space": RANGE },
])
def test_hyperparameter_validation_rejects_invalid(hp):
    with pytest.raises(ValidationError):
        Hyperparameter.model_validate(hp)


@pytest.mark.parametrize("hp", [
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": RANGE },
    { "name": "n", "type": "number", "promoted_value": 1, "testable_values": SET_NUMBERS },
    { "name": "boost", "type": "number", "promoted_value": 1.5, "testable_values": { "type": "range", "min": 0 }},
    { "name": "cap", "type": "number", "promoted_value": -3, "testable_values": { "type": "range", "max": 0 }},
    { "name": "any", "type": "number", "promoted_value": 7, "testable_values": { "type": "range" }},
    { "name": "b", "type": "boolean", "promoted_value": True },
    { "name": "b", "type": "boolean", "promoted_value": False, "testable_values": { "type": "set", "values": [True, False] }},
    { "name": "s", "type": "string", "promoted_value": "name.text", "testable_values": { "type": "set", "values": ["name.text", "name.ngram"] }},
])
def test_hyperparameter_validation_accepts_valid(hp):
    Hyperparameter.model_validate(hp)


def test_boolean_hyperparameter_gets_implicit_testable_values():
    hp = Hyperparameter.model_validate({ "name": "b", "type": "boolean", "promoted_value": True })
    assert hp.model_dump()["testable_values"] == { "type": "set", "values": [True, False] }


def test_strategy_rejects_duplicate_hyperparameter_names():
    hp = { "name": "name_boost", "type": "number", "promoted_value": 1, "testable_values": RANGE }
    with pytest.raises(ValidationError, match="unique"):
        StrategyCreate.model_validate(strategy_input(hyperparameters=[hp, hp]), context=mock_context())


def test_strategy_update_accepts_hyperparameters_and_promoted_from():
    doc = StrategyUpdate.model_validate({
        "workspace_id": WS,
        "hyperparameters": [{
            "name": "name_boost", "type": "number", "promoted_value": 3.0, "testable_values": RANGE,
        }],
        "promoted_from": {
            "strategy_id": "s", "run_id": "r", "variant_id": "v", "values": { "name_boost": 3.0 },
        },
    }, context=mock_context()).serialize()
    assert doc["hyperparameters"][0]["promoted_value"] == 3.0
    assert doc["promoted_from"]["variant_id"] == "v"


def test_strategy_update_checks_refs_only_when_template_and_hyperparameters_are_given():
    StrategyUpdate.model_validate(
        { "workspace_id": WS, "template": { "source": SOURCE }}, context=mock_context(),
    )
    with pytest.raises(ValidationError, match="undefined"):
        StrategyUpdate.model_validate(
            { "workspace_id": WS, "template": { "source": SOURCE }, "hyperparameters": [] },
            context=mock_context(),
        )


####  Scenarios  ###############################################################

def test_scenario_values_reserve_hp():
    with pytest.raises(ValidationError, match="reserved"):
        ScenarioCreate.model_validate(
            { "workspace_id": WS, "name": "x", "values": { "text": "a", "hp": 1 }}, context=mock_context(),
        )


####  Benchmarks  ##############################################################

def test_task_without_optimization_is_valid():
    assert TaskCreate().optimization is None


def test_task_optimization_defaults_and_serialization():
    task = TaskCreate.model_validate({ "optimization": {
        "algorithm": "random", "sample_size": 20, "seed": "s",
        "points_per_range": 7,
        "values_to_test": [
            { "name": "name_boost", "values": { "type": "range", "min": 0, "max": 100, "step": 10 }},
            { "name": "name_boost", "strategy_id": "s1", "enabled": False },
        ],
        "latency_constraint": { "stat": "median", "max_ms": 50 },
        "holdout": { "ratio": 0.3 },
    }})
    opt = task.optimization
    assert opt.objective.metric == "ndcg" and opt.objective.aggregation == "mean"
    assert opt.holdout.ratio == 0.3 and opt.store_hits_top_n == 3
    dumped = task.model_dump(by_alias=True)["optimization"]
    assert dumped["points_per_range"] == 7
    assert dumped["values_to_test"][0]["values"]["step"] == 10
    assert dumped["values_to_test"][1] == { "name": "name_boost", "strategy_id": "s1", "enabled": False }


@pytest.mark.parametrize("optimization", [
    { "algorithm": "bayesian" },
    { "sample_size": 0 },
    { "holdout": { "ratio": 0.95 }},
    { "holdout": { "ratio": -0.1 }},
    { "latency_constraint": { "max_ms": 0 }},
    { "latency_constraint": { "stat": "p99", "max_ms": 5 }},
    { "objective": { "metric": "err" }},
    { "max_concurrent_searches": 0 },
    { "unknown": 1 },
    { "points_per_range": 1 },
    # One entry per name and strategy
    { "values_to_test": [
        { "name": "a", "values": { "type": "set", "values": [1, 2] }},
        { "name": "a", "values": { "type": "set", "values": [3, 4] }},
    ]},
    # A range to test needs both bounds, and min below max
    { "values_to_test": [{ "name": "a", "values": { "type": "range", "min": 0 }}]},
    { "values_to_test": [{ "name": "a", "values": { "type": "range", "min": 2, "max": 1 }}]},
    # Step and count are mutually exclusive, and a log range uses count
    { "values_to_test": [{ "name": "a", "values": { "type": "range", "min": 1, "max": 2, "step": 1, "count": 3 }}]},
    { "values_to_test": [{ "name": "a", "values": { "type": "range", "min": 1, "max": 2, "step": 1, "log": True }}]},
    { "values_to_test": [{ "name": "a", "values": { "type": "range", "min": 0, "max": 2, "count": 3, "log": True }}]},
    { "values_to_test": [{ "name": "a", "values": { "type": "set", "values": [1] }}]},
    { "search_space_overrides": [] },
])
def test_task_optimization_rejects_invalid(optimization):
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({ "optimization": optimization })


def test_objective_metric_must_be_one_of_the_task_metrics():
    optimization = { "objective": { "metric": "mrr" }}
    TaskCreate.model_validate({ "optimization": optimization })  # mrr is a default metric
    with pytest.raises(ValidationError, match="task metrics"):
        TaskCreate.model_validate({ "metrics": ["ndcg"], "optimization": optimization })


def test_benchmark_create_and_update_accept_optimization():
    create = BenchmarkCreate.model_validate({
        "workspace_id": WS, "name": "b",
        "task": { "optimization": { "algorithm": "grid", "holdout": { "ratio": 0.2 }}},
    }, context=mock_context()).serialize()
    assert create["task"]["optimization"]["holdout"]["ratio"] == 0.2
    update = BenchmarkUpdate.model_validate({
        "workspace_id": WS, "task": { "optimization": { "algorithm": "random", "sample_size": 5 }},
    }, context=mock_context()).serialize()
    assert update["task"]["optimization"]["sample_size"] == 5


def test_optimization_model_dump_roundtrips():
    opt = Optimization.model_validate({ "algorithm": "random", "holdout": { "ratio": 0.5, "seed": "x" }})
    assert Optimization.model_validate(opt.model_dump()) == opt
