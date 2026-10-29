# Standard packages
import json
from types import SimpleNamespace

# Third-party packages
import pytest

# App packages
from server.api import runs

TEMPLATE_HP = '{"query":{"match":{"t":{"query":"{{text}}","boost":{{hp.boost}}}}}}'
TEMPLATE_PLAIN = '{"query":{"match":{"t":"{{text}}"}}}'


def response(body, status=200):
    return SimpleNamespace(body=body, meta=SimpleNamespace(status=status))


class FakeStudio:
    def __init__(self, scenario_ids):
        self.scenario_ids = scenario_ids
        self.updates = []

    def get(self, index, id, **kwargs):
        if index == "esrs-workspaces":
            return response({ "_source": { "index_pattern": "content", "rating_scale": { "max": 3 }}})
        raise Exception("not found")  # benchmark config: falls back to env defaults

    def search(self, index, body):
        if index == "esrs-judgements":
            hits = [
                { "_id": f"j-{sid}", "_source": {
                    "scenario_id": sid, "index": "content", "doc_id": "d1", "rating": 2,
                }}
                for sid in self.scenario_ids
            ]
        elif index == "esrs-scenarios":
            hits = [{ "_id": sid, "_source": { "values": { "text": f"query {sid}" }}} for sid in self.scenario_ids]
        else:
            hits = []
        return response({ "hits": { "hits": hits }})

    def update(self, **kwargs):
        self.updates.append(kwargs)
        return response({})


class FakeContent:
    """Scores a request by its boost: ndcg = boost / 10. Precision is flat."""
    def __init__(self):
        self.calls = []

    def rank_eval(self, index, body):
        self.calls.append(body)
        metric_name = next(iter(body["metric"]))
        details = {}
        for r in body["requests"]:
            boost = (r["params"].get("hp") or {}).get("boost", 1)
            score = boost / 10 if metric_name == "dcg" else 0.5
            details[r["id"]] = {
                "metric_score": score,
                "hits": [
                    { "hit": { "_index": "content", "_id": "d1" }, "rating": 2 },
                    { "hit": { "_index": "content", "_id": f"u-{boost}" }, "rating": None },
                ],
                "took": 10 + boost,
            }
        return response({ "details": details, "failures": {} })


@pytest.fixture
def setup(monkeypatch):
    scenario_ids = [f"sc{i:02d}" for i in range(10)]
    studio, content = FakeStudio(scenario_ids), FakeContent()
    monkeypatch.setattr(runs, "es", lambda name="studio": studio if name == "studio" else content)
    monkeypatch.setattr(runs.content, "make_index_relevance_fingerprints", lambda pattern: {})
    hp_source = {
        "name": "HP", "tags": ["hp"],
        "template": { "lang": "mustache", "source": TEMPLATE_HP },
        "hyperparameters": [{
            "name": "boost", "type": "number", "promoted_value": 1,
            "testable_values": { "type": "set", "values": [1, 2, 3] },
        }],
    }
    plain_source = { "name": "Plain", "tags": [], "template": { "lang": "mustache", "source": TEMPLATE_PLAIN }}
    candidates = {
        "strategies": [
            { "_id": "s1", "tags": ["hp"], "_source": hp_source },
            { "_id": "s2", "tags": [], "_source": plain_source },
        ],
        "scenarios": [{ "_id": sid, "tags": [] } for sid in scenario_ids],
    }
    monkeypatch.setattr(runs.benchmarks, "make_candidate_pool", lambda ws, task: candidates)
    return SimpleNamespace(studio=studio, content=content, scenario_ids=scenario_ids)


def evaluation(optimization=None):
    task = {
        "metrics": ["ndcg", "precision"], "k": 10, "requests": 0,
        "strategies": {}, "scenarios": {},
    }
    if optimization is not None:
        task["optimization"] = optimization
    return { "_id": "run1", "workspace_id": "ws", "benchmark_id": "bench", "task": task }


def searches(doc, strategy_id):
    return next(r for r in doc["results"] if r["strategy_id"] == strategy_id)["searches"]


def test_run_without_optimization_is_one_baseline_variant_per_strategy(setup):
    doc = runs.run(evaluation())
    assert doc["@meta"]["status"] == "completed"
    # No holdout, so every scenario is a tuning scenario and each strategy has one variant.
    assert len(searches(doc, "s1")) == 1 * 10
    assert len(searches(doc, "s2")) == 10
    assert len(doc["variants"]) == 2
    assert all(v["is_baseline"] and v["is_winner"] for v in doc["variants"])
    assert doc["summary"]["strategy_id"]["s2"]["optimization"]["score_basis"] == "in_sample"
    # Plain strategies don't get hp params.
    plain_requests = [
        r for body in setup.content.calls for r in body["requests"] if r["template_id"] == "s2"
    ]
    assert plain_requests and all("hp" not in r["params"] for r in plain_requests)


def test_grid_with_holdout_picks_winner_on_tuning_and_validates_on_holdout(setup):
    doc = runs.run(evaluation({
        "algorithm": "grid",
        "objective": { "metric": "ndcg", "aggregation": "mean" },
        "holdout": { "ratio": 0.3, "seed": "x" },
    }))
    assert doc["@meta"]["status"] == "completed"
    tuning = [ s for s in searches(doc, "s1") if s["split"] == "tuning" ]
    holdout = [ s for s in searches(doc, "s1") if s["split"] == "holdout" ]
    assert len(tuning) == 3 * 7          # 3 variants x 7 tuning scenarios
    assert len(holdout) == 2 * 3         # winner + baseline x 3 holdout scenarios
    tuning_ids = { s["scenario_id"] for s in tuning }
    holdout_ids = { s["scenario_id"] for s in holdout }
    assert not tuning_ids & holdout_ids

    variants = { v["variant_id"]: v for v in doc["variants"] if v["strategy_id"] == "s1" }
    assert len(variants) == 3
    winner = next(v for v in variants.values() if v["is_winner"])
    baseline = next(v for v in variants.values() if v["is_baseline"])
    assert winner["values"] == { "boost": 3 } and baseline["values"] == { "boost": 1 }
    # Only the winner and the baseline were tested on the holdout.
    assert sum(1 for v in variants.values() if v["aggregates"]["holdout"]) == 2
    assert { s["variant_id"] for s in holdout } == { winner["variant_id"], baseline["variant_id"] }

    opt = doc["summary"]["strategy_id"]["s1"]["optimization"]
    assert opt["variant_id"] == winner["variant_id"]
    assert opt["baseline_variant_id"] == baseline["variant_id"]
    assert opt["variant_count"] == 3
    assert opt["score_basis"] == "holdout"
    assert opt["holdout"]["metrics"]["ndcg"]["avg"] == pytest.approx(0.3)
    assert opt["baseline_holdout"]["metrics"]["ndcg"]["avg"] == pytest.approx(0.1)
    # The headline score is the winner's holdout score
    assert doc["summary"]["strategy_id"]["s1"]["_total"]["metrics"]["ndcg"]["avg"] == pytest.approx(0.3)
    # Scenario-level metrics still cover every scenario of the winner
    assert len(doc["summary"]["strategy_id"]["s1"]["by_scenario_id"]) == 10

    # The single-variant strategy still sees every scenario once
    plain = searches(doc, "s2")
    assert len(plain) == 10 and {s["split"] for s in plain} == { "tuning", "holdout" }
    # Seeds are recorded for reproducibility
    assert doc["task"]["optimization"]["seed"] == "bench"
    # Progress ends complete: planned holdout requests all ran
    assert doc["progress"]["requests_total"] == doc["progress"]["requests_completed"]
    assert doc["task"]["requests"] == doc["progress"]["requests_completed"]


def test_request_ids_have_three_segments_and_pass_hp_params(setup):
    runs.run(evaluation({ "algorithm": "grid" }))
    hp_requests = [
        r for body in setup.content.calls for r in body["requests"] if r["template_id"] == "s1"
    ]
    assert hp_requests
    for r in hp_requests:
        strategy_id, variant_id, scenario_id = r["id"].split("~", 2)
        assert strategy_id == "s1" and scenario_id.startswith("sc")
        assert r["params"]["hp"]["boost"] in (1, 2, 3)
        assert r["params"]["text"].startswith("query")


def test_latency_constraint_excludes_slow_winner(setup):
    # took = 10 + boost, so boost=3 takes 13ms. A 12ms limit excludes it.
    doc = runs.run(evaluation({
        "algorithm": "grid",
        "latency_constraint": { "stat": "median", "max_ms": 12 },
    }))
    winner = next(v for v in doc["variants"] if v["strategy_id"] == "s1" and v["is_winner"])
    assert winner["values"] == { "boost": 2 }
    slow = next(v for v in doc["variants"] if v["strategy_id"] == "s1" and v["values"] == { "boost": 3 })
    assert slow["violates_constraint"] and not slow["is_winner"]


def test_hits_are_stored_only_for_top_variants_winner_and_baseline(setup):
    doc = runs.run(evaluation({ "algorithm": "grid", "store_hits_top_n": 1 }))
    variants = { v["variant_id"]: v for v in doc["variants"] if v["strategy_id"] == "s1" }
    kept = { vid for vid, v in variants.items() if v["hits_stored"] }
    assert len(kept) == 2  # winner (boost 3, also rank 1) and baseline (boost 1)
    for s in searches(doc, "s1"):
        assert bool(s["hits"]) == (s["variant_id"] in kept)
    # Unrated docs cover every variant even though hits were dropped
    unrated_variants = { v for u in doc["unrated_docs"] for v in u["variants"] }
    assert set(variants) <= unrated_variants


def test_random_search_samples_sample_size_variants(setup):
    doc = runs.run(evaluation({
        "algorithm": "random", "sample_size": 2, "seed": "s",
    }))
    assert len([v for v in doc["variants"] if v["strategy_id"] == "s1"]) == 2


def test_run_over_the_search_limit_fails_before_searching(setup, monkeypatch):
    monkeypatch.setattr(runs.optimization, "MAX_SEARCHES", 5)
    with pytest.raises(ValueError):
        runs.run(evaluation({ "algorithm": "grid" }))
    assert setup.content.calls == []


def test_undefined_hyperparameter_reference_fails_the_run(setup, monkeypatch):
    bad = {
        "name": "Bad", "tags": [],
        "template": { "lang": "mustache", "source": TEMPLATE_HP },
    }
    monkeypatch.setattr(runs.benchmarks, "make_candidate_pool", lambda ws, task: {
        "strategies": [{ "_id": "s1", "tags": [], "_source": bad }],
        "scenarios": [{ "_id": "sc00", "tags": [] }],
    })
    with pytest.raises(ValueError, match="undefined hyperparameters"):
        runs.run(evaluation())


def test_hyperparameter_values_replace_the_promoted_values_of_a_test_run(setup):
    # 50 isn't one of the valid testable values {1, 2, 3}, which is allowed for a test.
    ev = evaluation()
    ev["task"]["hyperparameter_values"] = { "boost": 50 }
    doc = runs.run(ev)
    assert doc["task"]["hyperparameter_values"] == { "boost": 50 }
    assert doc["@meta"]["status"] == "completed"
    hp_requests = [
        r for body in setup.content.calls for r in body["requests"] if r["template_id"] == "s1"
    ]
    assert hp_requests and all(r["params"]["hp"] == { "boost": 50 } for r in hp_requests)
    variants = [ v for v in doc["variants"] if v["strategy_id"] == "s1" ]
    assert len(variants) == 1 and variants[0]["values"] == { "boost": 50 }
    # The strategy keeps its own promoted value
    assert doc["runtime"]["strategies"]["s1"]["hyperparameters"][0]["promoted_value"] == 1


@pytest.mark.parametrize("values, optimization, store_results, message", [
    ({ "nope": 1 }, None, False, "undefined hyperparameters"),
    ({ "boost": "high" }, None, False, "must be a valid number"),
    ({ "boost": 2 }, { "algorithm": "grid" }, False, "can't be used with task.optimization"),
    ({ "boost": 2 }, None, True, "can't be used when storing results"),
    ([ 1 ], None, False, "must be an object"),
])
def test_invalid_hyperparameter_values_fail_the_run(setup, values, optimization, store_results, message):
    ev = evaluation(optimization)
    ev["task"]["hyperparameter_values"] = values
    with pytest.raises(ValueError, match=message):
        runs.run(ev, store_results=store_results)
    assert setup.content.calls == []


def test_stored_run_writes_variant_aware_documents(setup, monkeypatch):
    captured = {}
    def fake_bulk(client, actions, **kwargs):
        captured["actions"] = list(actions)
        return len(captured["actions"]), []
    monkeypatch.setattr(runs.helpers, "bulk", fake_bulk)
    runs.run(evaluation({
        "algorithm": "grid", "holdout": { "ratio": 0.3, "seed": "x" },
    }), store_results=True)
    by_index = {}
    for a in captured["actions"]:
        by_index.setdefault(a["_index"], []).append(a)

    results = by_index[runs.RESULTS_INDEX_NAME]
    assert len({ a["_id"] for a in results }) == len(results)  # ids are unique per variant/split
    s1 = [ a["_source"] for a in results if a["_source"]["strategy_id"] == "s1" ]
    assert len(s1) == 3 * 7 + 2 * 3
    assert all(d["variant_id"] and d["split"] in ("tuning", "holdout") for d in s1)
    assert all("coverage" in d for d in s1)

    variants = by_index[runs.RUNTIME_VARIANTS_INDEX_NAME]
    assert len(variants) == 3 + 1
    assert all("aggregates" in a["_source"] and "values" in a["_source"] for a in variants)

    strategies = {
        a["_source"]["strategy_id"]: a["_source"] for a in by_index[runs.RUNTIME_STRATEGIES_INDEX_NAME]
    }
    assert strategies["s1"]["variant_count"] == 3
    assert strategies["s1"]["winner_variant_id"]
    scenarios = by_index[runs.RUNTIME_SCENARIOS_INDEX_NAME]
    assert sorted({ a["_source"]["split"] for a in scenarios }) == ["holdout", "tuning"]
    assert all("variants" in a["_source"] for a in by_index[runs.UNRATED_DOCS_INDEX_NAME])
    # The run doc stays small: no variants or results on it
    final = [u for u in setup.studio.updates if "doc" in u and "summary" in u["doc"]][-1]["doc"]
    assert "variants" not in final and "results" not in final


def test_max_concurrent_searches_is_passed_to_rank_eval(setup):
    runs.run(evaluation({ "algorithm": "grid", "max_concurrent_searches": 4 }))
    assert all(body["max_concurrent_searches"] == 4 for body in setup.content.calls)


def test_invalid_variant_fails_alone_instead_of_failing_the_whole_call(setup):
    from elastic_transport import ApiResponseMeta, HttpHeaders
    from elasticsearch import BadRequestError

    original = setup.content.rank_eval
    bad_boost = 2

    def rank_eval(index, body):
        # Elasticsearch rejects the whole call when any rendered template is invalid.
        for r in body["requests"]:
            if (r["params"].get("hp") or {}).get("boost") == bad_boost:
                meta = ApiResponseMeta(
                    status=400, http_version="1.1", headers=HttpHeaders(), duration=0, node=None,
                )
                raise BadRequestError("x_content_parse_exception", meta, {})
        return original(index, body)

    setup.content.rank_eval = rank_eval
    doc = runs.run(evaluation({ "algorithm": "grid", "objective": { "metric": "ndcg" }}))
    assert doc["@meta"]["status"] == "completed"
    by_boost = { v["values"]["boost"]: v for v in doc["variants"] if v["strategy_id"] == "s1" }
    assert by_boost[2]["score"] is None
    assert by_boost[1]["score"] is not None and by_boost[3]["score"] is not None
    # The valid variants still compete, and the invalid one can't win.
    assert not by_boost[2]["is_winner"]
    assert any(v["is_winner"] for v in by_boost.values())
    failures = next(r for r in doc["results"] if r["strategy_id"] == "s1")["failures"]
    assert failures and all(f["variant_id"] == by_boost[2]["variant_id"] for f in failures)


def test_values_to_test_narrow_the_variants_of_a_run(setup):
    doc = runs.run(evaluation({
        "algorithm": "grid",
        "values_to_test": [{ "name": "boost", "values": { "type": "set", "values": [1, 3] }}],
    }))
    boosts = sorted(v["values"]["boost"] for v in doc["variants"] if v["strategy_id"] == "s1")
    assert boosts == [1, 3]


def test_unbounded_hyperparameter_needs_a_finite_range_to_test(setup, monkeypatch):
    unbounded = {
        "name": "HP", "tags": [],
        "template": { "lang": "mustache", "source": TEMPLATE_HP },
        "hyperparameters": [{
            "name": "boost", "type": "number", "promoted_value": 1,
            "testable_values": { "type": "range", "min": 0 },
        }],
    }
    monkeypatch.setattr(runs.benchmarks, "make_candidate_pool", lambda ws, task: {
        "strategies": [{ "_id": "s1", "tags": [], "_source": unbounded }],
        "scenarios": [{ "_id": "sc00", "tags": [] }],
    })
    with pytest.raises(ValueError, match="unbounded"):
        runs.run(evaluation({ "algorithm": "grid" }))
    # A finite range to test makes it runnable, as does not testing it
    doc = runs.run(evaluation({
        "algorithm": "grid",
        "values_to_test": [{ "name": "boost", "values": { "type": "range", "min": 1, "max": 3, "step": 1 }}],
    }))
    assert sorted(v["values"]["boost"] for v in doc["variants"]) == [1, 2, 3]
    doc = runs.run(evaluation({ "algorithm": "grid", "values_to_test": [{ "name": "boost", "enabled": False }]}))
    assert [v["values"]["boost"] for v in doc["variants"]] == [1]


def test_probe_reports_a_variant_that_elasticsearch_rejects(setup):
    from elastic_transport import ApiResponseMeta, HttpHeaders
    from elasticsearch import BadRequestError

    original = setup.content.rank_eval

    def rank_eval(index, body):
        if any((r["params"].get("hp") or {}).get("boost") == 2 for r in body["requests"]):
            meta = ApiResponseMeta(status=400, http_version="1.1", headers=HttpHeaders(), duration=0, node=None)
            raise BadRequestError("x_content_parse_exception", meta, { "error": { "reason": "bad boost" }})
        return original(index, body)

    setup.content.rank_eval = rank_eval
    source = { "name": "HP", "template": { "source": TEMPLATE_HP }}
    plans = { "s1": [
        { "variant_id": f"v{b}", "values": { "boost": b } } for b in (1, 2, 3)
    ]}
    errors = []
    out = runs._probe_latency(
        "ws", { "s1": source }, plans, setup.scenario_ids, { "dcg": { "k": 10, "normalize": True }},
        "content", errors=errors,
    )
    # One report per rejected variant, however many scenarios and passes failed
    assert len(errors) == 1
    assert "HP" in errors[0] and '"boost":2' in errors[0]
    # The valid variants still produce timings
    assert out["s1"]["samples"] > 0
