# Standard packages
from types import SimpleNamespace

# Third-party packages
import pytest

# App packages
from server import utils
from server.api import optimization, runs, strategies

SOURCE = '{"query":{"match":{"{{hp.field}}":{"query":"{{text}}","boost":{{hp.boost}}}}}}'
HPS = [
    { "name": "boost", "type": "number", "promoted_value": 2.0,
      "testable_values": { "type": "range", "min": 0, "max": 4 }},
    { "name": "field", "type": "string", "promoted_value": "name.text",
      "testable_values": { "type": "set", "values": ["name.text", "name.ngram"] }},
]
FINGERPRINT = utils.fingerprint([SOURCE])


def response(body, status=200):
    return SimpleNamespace(body=body, meta=SimpleNamespace(status=status))


####  strategies.render  #######################################################

def test_render_applies_promoted_values_and_keeps_scenario_variables():
    out = strategies.render(template={ "source": SOURCE }, hyperparameters=HPS)
    assert out["values"] == { "boost": 2.0, "field": "name.text" }
    assert out["source"] == '{"query":{"match":{"name.text":{"query":"{{text}}","boost":2.0}}}}'


def test_render_overrides_values_and_validates_them():
    out = strategies.render(template={ "source": SOURCE }, hyperparameters=HPS, values={ "boost": 3 })
    assert '"boost":3' in out["source"]
    with pytest.raises(ValueError, match="not a defined"):
        strategies.render(template={ "source": SOURCE }, hyperparameters=HPS, values={ "nope": 1 })
    with pytest.raises(ValueError, match="not a valid number"):
        strategies.render(template={ "source": SOURCE }, hyperparameters=HPS, values={ "boost": "x" })


def test_render_requires_defined_references(monkeypatch):
    with pytest.raises(ValueError, match="undefined"):
        strategies.render(template={ "source": SOURCE }, hyperparameters=HPS[:1])
    with pytest.raises(ValueError, match="template"):
        strategies.render()


def test_render_loads_a_saved_strategy(monkeypatch):
    monkeypatch.setattr(strategies, "get", lambda _id: {
        "_source": { "template": { "source": SOURCE }, "hyperparameters": HPS },
    })
    assert strategies.render(_id="s1")["values"]["field"] == "name.text"


####  strategies.promote  ######################################################

@pytest.fixture
def promotion(monkeypatch):
    values = { "boost": 3.0, "field": "name.ngram" }
    variant = {
        "workspace_id": "ws", "strategy_id": "s1", "variant_id": "v-123456789", "values": values,
    }
    snapshot = {
        "name": "Boosted", "tags": ["bm25"], "template": { "lang": "mustache", "source": SOURCE },
        "hyperparameters": HPS, "_fingerprint": FINGERPRINT,
    }
    monkeypatch.setattr(runs, "get_variant", lambda run_id, variant_id, strategy_id=None: variant)
    monkeypatch.setattr(runs, "get_runtime_strategy", lambda run_id, strategy_id: { "item": snapshot })
    calls = SimpleNamespace(update=[], create=[])
    ok = { "errors": False, "items": [{ "update": { "status": 200 }}] }
    monkeypatch.setattr(strategies, "update", lambda docs, user=None, via=None: calls.update.append((docs, user, via)) or ok)
    monkeypatch.setattr(strategies, "create", lambda docs, user=None, via=None: calls.create.append((docs, user, via)) or {
        "errors": False, "items": [{ "index": { "status": 201 }}],
    })
    monkeypatch.setattr(strategies, "get", lambda _id: { "_source": {
        "template": snapshot["template"], "hyperparameters": HPS,
    }})
    return SimpleNamespace(calls=calls, snapshot=snapshot, values=values)


def test_promote_update_values_sets_promoted_values_and_records_source(promotion):
    out = strategies.promote("run1", "v-123456789", user="dave", via="mcp")
    assert out["mode"] == "update_values" and out["strategy_id"] == "s1" and out["warnings"] == []
    (docs, user, via), = promotion.calls.update
    assert user == "dave" and via == "mcp"
    doc = docs[0]
    assert doc["_id"] == "s1" and doc["workspace_id"] == "ws"
    promoted = { h["name"]: h["promoted_value"] for h in doc["hyperparameters"] }
    assert promoted == promotion.values
    # The definitions and valid testable values are kept
    assert all(h["testable_values"] for h in doc["hyperparameters"])
    source = doc["promoted_from"]
    assert source["strategy_id"] == "s1" and source["run_id"] == "run1"
    assert source["variant_id"] == "v-123456789" and source["values"] == promotion.values
    assert source["promoted_at"]


def test_promote_update_warns_when_template_changed(promotion, monkeypatch):
    monkeypatch.setattr(strategies, "get", lambda _id: { "_source": {
        "template": { "source": SOURCE + " " }, "hyperparameters": HPS,
    }})
    out = strategies.promote("run1", "v-123456789")
    assert any("template changed" in w for w in out["warnings"])


def test_promote_update_rejects_removed_or_retyped_hyperparameters(promotion, monkeypatch):
    monkeypatch.setattr(strategies, "get", lambda _id: { "_source": {
        "template": promotion.snapshot["template"], "hyperparameters": HPS[:1],
    }})
    with pytest.raises(ValueError, match="no longer defines"):
        strategies.promote("run1", "v-123456789")
    retyped = [{ **HPS[0], "type": "string", "promoted_value": "a", "testable_values": None }, HPS[1]]
    monkeypatch.setattr(strategies, "get", lambda _id: { "_source": {
        "template": promotion.snapshot["template"], "hyperparameters": retyped,
    }})
    with pytest.raises(ValueError, match="no longer fits"):
        strategies.promote("run1", "v-123456789")
    narrowed = [{ **HPS[0], "promoted_value": 1.0, "testable_values": { "type": "range", "min": 0, "max": 2 }}, HPS[1]]
    monkeypatch.setattr(strategies, "get", lambda _id: { "_source": {
        "template": promotion.snapshot["template"], "hyperparameters": narrowed,
    }})
    with pytest.raises(ValueError, match="no longer one of the valid testable values"):
        strategies.promote("run1", "v-123456789")


def test_promote_fork_creates_strategy_from_the_run_snapshot(promotion):
    out = strategies.promote("run1", "v-123456789", mode="fork", name="Forked")
    assert out["mode"] == "fork" and out["strategy_id"] != "s1"
    assert not promotion.calls.update
    (docs, _, _), = promotion.calls.create
    doc = docs[0]
    assert doc["_id"] == out["strategy_id"] and doc["name"] == "Forked"
    assert doc["tags"] == ["bm25"] and doc["template"]["source"] == SOURCE
    assert { h["name"]: h["promoted_value"] for h in doc["hyperparameters"] } == promotion.values
    assert doc["hyperparameters"][0]["testable_values"] == HPS[0]["testable_values"]
    assert doc["promoted_from"]["strategy_id"] == "s1"
    # The default name derives from the source name and variant ID
    out = strategies.promote("run1", "v-123456789", mode="fork")
    assert promotion.calls.create[-1][0][0]["name"] == "Boosted (v-123456)"


def test_promote_rejects_unknown_mode_and_failed_writes(promotion, monkeypatch):
    with pytest.raises(ValueError, match="mode"):
        strategies.promote("run1", "v-123456789", mode="merge")
    monkeypatch.setattr(strategies, "update", lambda docs, user=None, via=None: {
        "errors": True, "items": [{ "update": { "status": 400, "error": "bad" }}],
    })
    with pytest.raises(ValueError, match="promotion failed"):
        strategies.promote("run1", "v-123456789")


####  runs.estimate  ###########################################################

class EstimateStudio:
    def __init__(self, judged, sources):
        self.judged, self.sources = judged, sources

    def search(self, index, body):
        if index == "esrs-judgements":
            buckets = [{ "key": sid } for sid in self.judged]
            return response({ "aggregations": { "scenarios": { "buckets": buckets }}})
        raise AssertionError(index)


@pytest.fixture
def estimating(monkeypatch):
    scenario_ids = [f"sc{i:02d}" for i in range(40)]
    sources = {
        "s1": { "name": "HP", "template": { "source": SOURCE }, "hyperparameters": HPS },
        "s2": { "name": "Plain", "template": { "source": '{"q":"{{text}}"}' }},
    }
    candidates = {
        "strategies": [{ "_id": k, "tags": [], "_source": v } for k, v in sources.items()],
        "scenarios": [{ "_id": s, "tags": [] } for s in scenario_ids],
    }
    monkeypatch.setattr(runs.benchmarks, "make_candidate_pool", lambda ws, task: candidates)
    studio = EstimateStudio(scenario_ids, sources)
    monkeypatch.setattr(runs, "es", lambda name="studio": studio)
    return SimpleNamespace(scenario_ids=scenario_ids, sources=sources)


def test_estimate_counts_variants_and_searches_without_holdout(estimating):
    task = { "metrics": ["ndcg", "mrr"], "optimization": { "algorithm": "grid" }}
    out = runs.estimate("ws", task)
    by_id = { s["_id"]: s for s in out["strategies"] }
    assert by_id["s1"]["variants"] == 5 * 2 and by_id["s2"]["variants"] == 1
    assert out["variants"] == 11
    assert out["scenarios"] == { "candidates": 40, "with_judgements": 40, "tuning": 40, "holdout": 0 }
    # sum(variants) x scenarios x passes (one pass per metric)
    assert out["searches"] == { "tuning": 11 * 40 * 2, "holdout": 0, "total": 11 * 40 * 2 }
    assert out["rank_eval_calls"] == 2 * 2  # one call per strategy per metric
    assert out["errors"] == [] and out["duration"] is None
    assert any("in-sample" in w for w in out["warnings"])


def test_estimate_accounts_for_the_holdout_split(estimating):
    task = { "metrics": ["ndcg"], "optimization": { "holdout": { "ratio": 0.25 }}}
    out = runs.estimate("ws", task)
    assert out["scenarios"]["tuning"] == 30 and out["scenarios"]["holdout"] == 10
    assert out["searches"]["tuning"] == 11 * 30
    assert out["searches"]["holdout"] == (2 + 1) * 10
    assert not any("in-sample" in w for w in out["warnings"])


def test_estimate_warns_about_a_small_holdout(estimating):
    out = runs.estimate("ws", { "metrics": ["ndcg"], "optimization": { "holdout": { "ratio": 0.25 }}})
    assert any("too few" in w for w in out["warnings"])  # 10 < 30


def test_estimate_without_optimization_counts_one_variant_per_strategy(estimating):
    out = runs.estimate("ws", { "metrics": ["ndcg"] })
    assert out["variants"] == 2
    assert out["searches"]["total"] == 2 * 40


def test_estimate_values_to_test_change_the_variant_count(estimating):
    task = { "metrics": ["ndcg"], "optimization": { "values_to_test": [
        { "name": "boost", "values": { "type": "range", "min": 0, "max": 4, "step": 0.5 }},
    ]}}
    # 9 boosts x 2 fields. The baseline (boost 2) is on the grid.
    assert { s["_id"]: s["variants"] for s in runs.estimate("ws", task)["strategies"] }["s1"] == 9 * 2
    # A hyperparameter that isn't tested keeps its promoted value
    task = { "metrics": ["ndcg"], "optimization": { "values_to_test": [{ "name": "boost", "enabled": False }]}}
    assert { s["_id"]: s["variants"] for s in runs.estimate("ws", task)["strategies"] }["s1"] == 2
    # The points per range apply to ranges without a step or count
    task = { "metrics": ["ndcg"], "optimization": { "points_per_range": 3 }}
    assert { s["_id"]: s["variants"] for s in runs.estimate("ws", task)["strategies"] }["s1"] == 3 * 2


def test_estimate_reports_limit_errors(estimating, monkeypatch):
    monkeypatch.setattr(optimization, "MAX_SEARCHES", 100)
    out = runs.estimate("ws", { "metrics": ["ndcg"], "optimization": {} })
    assert any("maximum" in e for e in out["errors"])


def test_estimate_reports_unbounded_values_without_a_finite_range_to_test(estimating):
    estimating.sources["s1"]["hyperparameters"] = [
        { "name": "boost", "type": "number", "promoted_value": 2.0, "testable_values": { "type": "range", "min": 0 }},
        HPS[1],
    ]
    task = { "metrics": ["ndcg"], "optimization": {} }
    out = runs.estimate("ws", task)
    assert any("unbounded" in e and "boost" in e for e in out["errors"])
    # A finite range to test resolves it, and so does not testing the hyperparameter
    task["optimization"]["values_to_test"] = [{ "name": "boost", "values": { "type": "range", "min": 1, "max": 3 }}]
    assert runs.estimate("ws", task)["errors"] == []
    task["optimization"]["values_to_test"] = [{ "name": "boost", "enabled": False }]
    assert runs.estimate("ws", task)["errors"] == []


def test_estimate_reports_values_to_test_outside_the_testable_values(estimating):
    task = { "metrics": ["ndcg"], "optimization": { "values_to_test": [
        { "name": "boost", "values": { "type": "range", "min": 0, "max": 40 }},
    ]}}
    assert any("outside the valid testable values" in e for e in runs.estimate("ws", task)["errors"])


def test_estimate_includes_execution_settings(estimating):
    out = runs.estimate("ws", { "metrics": ["ndcg"], "rank_eval_batch_size": 20, "rank_eval_batch_delay": 100,
                                "optimization": { "max_concurrent_searches": 4 }})
    assert out["execution"] == {
        "max_concurrent_searches": 4, "rank_eval_batch_size": 20, "rank_eval_batch_delay_ms": 100,
    }
    # 10 variants x 40 scenarios = 400 requests in 20 calls for s1, 40 requests in 2 calls for s2
    assert out["rank_eval_calls"] == 20 + 2


def test_dry_run_of_create_estimates_without_creating(estimating, monkeypatch):
    created = []
    monkeypatch.setattr(runs, "es", lambda name="studio": SimpleNamespace(
        index=lambda **kw: created.append(kw), search=EstimateStudio(estimating.scenario_ids, {}).search,
    ))
    out = runs.create("ws", "bench", { "metrics": ["ndcg"] }, dry_run=True)
    assert out["searches"]["total"] == 2 * 40 and created == []


####  runs.get_variants and runs.get_optimization_summary  #####################

def variant_doc(vid, boost, ndcg, took, *, baseline=False, winner=False, holdout=None, coverage=0.9, strategy="s1"):
    def agg(score):
        return {
            "n": 5, "metrics": { "ndcg": { "avg": score, "median": score, "min": score, "max": score }},
            "took": { "avg": took, "median": took, "p90": took, "n": 5 }, "coverage": coverage,
        }
    return {
        "strategy_id": strategy, "variant_id": vid, "workspace_id": "ws", "is_baseline": baseline,
        "is_winner": winner, "values": { "boost": boost, "field": "name.text" }, "hits_stored": True,
        "aggregates": { "tuning": agg(ndcg), "holdout": agg(holdout) if holdout is not None else None },
    }


@pytest.fixture
def stored_run(monkeypatch):
    run = { "_source": { "task": {
        "metrics": ["ndcg", "mrr"],
        "optimization": { "objective": { "metric": "ndcg", "aggregation": "mean" },
                          "holdout": { "ratio": 0.3 }},
    }}}
    variants = [
        variant_doc("a", 1.0, 0.40, 10, baseline=True, holdout=0.38),
        variant_doc("b", 2.0, 0.55, 40, winner=True, holdout=0.50),
        variant_doc("c", 3.0, 0.50, 5),
        variant_doc("d", 4.0, 0.10, 8),
    ]
    snapshot = { "strategy_id": "s1", "item": { "name": "HP", "_resolved_hyperparameters": [
        { "name": "boost", "type": "number", "promoted_value": 2.0, "testable_values": {
            "type": "range", "min": 1, "max": 4 }, "values_to_test": {
            "type": "range", "min": 1, "max": 4, "step": 1 }},
        { "name": "field", "type": "string", "promoted_value": "name.text", "testable_values": {
            "type": "set", "values": ["name.text", "name.ngram"] }, "values_to_test": None},
    ]}}
    monkeypatch.setattr(runs, "get", lambda _id: run)
    monkeypatch.setattr(runs, "_fetch_all_run_collection", lambda index, run_id, **kw: [
        v for v in variants
        if all(f["term"]["strategy_id"] == v["strategy_id"] for f in kw.get("extra_filters") or [])
    ])
    monkeypatch.setattr(runs, "_paginate_run_collection", lambda index, run_id, **kw: { "items": [snapshot] })
    monkeypatch.setattr(runs, "get_runtime_strategies", lambda run_id: { "items": [snapshot] })
    monkeypatch.setattr(runs, "es", lambda name="studio": SimpleNamespace(search=lambda **kw: response({
        "aggregations": { "split": { "buckets": [
            { "key": "tuning", "doc_count": 70 }, { "key": "holdout", "doc_count": 30 },
        ]}},
    })))
    return SimpleNamespace(variants=variants)


def test_get_variants_ranks_by_the_runs_objective(stored_run):
    out = runs.get_variants("run1", "s1")
    assert [v["variant_id"] for v in out["items"]] == ["b", "c", "a", "d"]
    assert [v["rank"] for v in out["items"]] == [1, 2, 3, 4]
    assert out["items"][0]["is_winner"] and out["items"][0]["is_run_winner"]
    assert out["ranking"]["exploratory"] is False
    assert out["total"] == 4 and [h["name"] for h in out["hyperparameters"]] == ["boost", "field"]


def test_get_variants_reranks_under_another_constraint_as_exploratory(stored_run):
    out = runs.get_variants("run1", "s1", latency_constraint={ "stat": "median", "max_ms": 20 })
    assert out["ranking"]["exploratory"] is True
    # b (40ms) violates the constraint: c wins, but b stays in the list and remains the run winner
    assert out["items"][0]["variant_id"] == "c" and out["items"][0]["is_winner"]
    b = next(v for v in out["items"] if v["variant_id"] == "b")
    assert b["violates_constraint"] and not b["is_winner"] and b["is_run_winner"]
    assert out["items"][-1]["variant_id"] == "b"


def test_get_variants_sorts_and_paginates(stored_run):
    out = runs.get_variants("run1", "s1", sort="hp:boost", descending=True, size=2, page=2)
    assert [v["variant_id"] for v in out["items"]] == ["b", "a"]
    assert out["total"] == 4 and out["page"] == 2
    assert [v["variant_id"] for v in runs.get_variants("run1", "s1", sort="took")["items"]] == ["c", "d", "a", "b"]


def test_get_optimization_summary_is_compact_and_holdout_based(stored_run):
    out = runs.get_optimization_summary("run1", top_n=2)
    assert out["score_basis"] == "holdout" and out["scenarios"] == { "tuning": 70, "holdout": 30 }
    s1, = out["strategies"]
    assert s1["variant_count"] == 4 and len(s1["top_variants"]) == 2
    assert s1["winner"]["variant_id"] == "b" and s1["winner"]["holdout_score"] == 0.5
    assert s1["baseline"]["variant_id"] == "a" and s1["baseline"]["holdout_score"] == 0.38
    assert [v["variant_id"] for v in s1["top_variants"]] == ["b", "c"]
    # boost matters, field doesn't vary
    assert [s["name"] for s in s1["sensitivity"]] == ["boost", "field"]
    assert s1["sensitivity"][0]["spread"] > s1["sensitivity"][1]["spread"] == 0
    assert s1["sensitivity"][0]["points"][0] == [1.0, 0.4]
    assert s1["warnings"] == []


def test_get_optimization_summary_warns_about_coverage_holdout_size_and_no_gain(stored_run, monkeypatch):
    stored_run.variants[1]["aggregates"]["tuning"]["coverage"] = 0.2
    stored_run.variants[1]["aggregates"]["holdout"]["metrics"]["ndcg"] = { "avg": 0.3, "median": 0.3, "min": 0, "max": 1 }
    monkeypatch.setattr(runs, "es", lambda name="studio": SimpleNamespace(search=lambda **kw: response({
        "aggregations": { "split": { "buckets": [
            { "key": "tuning", "doc_count": 90 }, { "key": "holdout", "doc_count": 5 },
        ]}},
    })))
    warnings = runs.get_optimization_summary("run1")["strategies"][0]["warnings"]
    assert any("coverage" in w for w in warnings)
    assert any("too few" in w for w in warnings)
    assert any("did not help" in w for w in warnings)


def test_get_optimization_summary_without_holdout_is_labeled_in_sample(stored_run, monkeypatch):
    monkeypatch.setattr(runs, "es", lambda name="studio": SimpleNamespace(search=lambda **kw: response({
        "aggregations": { "split": { "buckets": [{ "key": "tuning", "doc_count": 100 }]}},
    })))
    out = runs.get_optimization_summary("run1")
    assert out["score_basis"] == "in_sample"
    assert any("in-sample" in w for w in out["strategies"][0]["warnings"])


####  runs.get_unrated_docs  ###################################################

def test_unrated_docs_winners_only_filters_by_winning_variants(monkeypatch):
    calls = {}
    def fake_fetch(index, run_id, **kwargs):
        calls["fetch"] = (index, kwargs)
        return [{ "variant_id": "v2" }, { "variant_id": "v1" }, { "variant_id": "v2" }]
    def fake_paginate(index, run_id, size, page, **kwargs):
        calls["paginate"] = kwargs
        return { "items": [] }
    monkeypatch.setattr(runs, "_fetch_all_run_collection", fake_fetch)
    monkeypatch.setattr(runs, "_paginate_run_collection", fake_paginate)

    runs.get_unrated_docs("r1", winners_only=True)

    assert calls["fetch"][1]["extra_filters"] == [{ "term": { "is_winner": True }}]
    assert calls["paginate"]["extra_filters"] == [{ "terms": { "variants": ["v1", "v2"] }}]


def test_unrated_docs_without_winners_only_adds_no_filter(monkeypatch):
    calls = {}
    monkeypatch.setattr(runs, "_paginate_run_collection", lambda *a, **kw: calls.update(kw) or { "items": [] })
    runs.get_unrated_docs("r1")
    assert calls["extra_filters"] is None
