# Third-party packages
import pytest

# App packages
from server import utils
from server.api import optimization as opt


def hp(name, type_, promoted, testable=None):
    d = { "name": name, "type": type_, "promoted_value": promoted }
    if testable is not None:
        d["testable_values"] = testable
    return d


def rng(lo=None, hi=None):
    d = { "type": "range" }
    if lo is not None:
        d["min"] = lo
    if hi is not None:
        d["max"] = hi
    return d


def values_set(*values):
    return { "type": "set", "values": list(values) }


def resolved(*hps, values_to_test=None, strategy_id="s1", points=5, optimize=True):
    return opt.resolve_hyperparameters(list(hps), values_to_test, strategy_id, points, optimize)


####  Values to test  ##########################################################

def test_overrides_replace_promoted_values_outside_the_testable_values():
    h = opt.resolve_hyperparameters(
        [hp("b", "number", 1, rng(0, 5)), hp("m", "string", "and", values_set("and", "or"))],
        None, "s1", 5, False, { "b": 50, "m": "xor" },
    )
    assert [x["promoted_value"] for x in h] == [50, "xor"]
    assert all(x["values_to_test"] is None for x in h)


@pytest.mark.parametrize("name, value", [("b", "high"), ("b", True), ("m", 'a"b'), ("m", 3)])
def test_overrides_must_fit_the_type(name, value):
    with pytest.raises(ValueError):
        opt.resolve_hyperparameters(
            [hp("b", "number", 1, rng(0, 5)), hp("m", "string", "and", values_set("and", "or"))],
            None, "s1", 5, False, { name: value },
        )


def test_grid_values_step_includes_both_ends():
    h = resolved(
        hp("b", "number", 1.0, rng(0, 1)),
        values_to_test=[{ "name": "b", "values": { "type": "range", "min": 0, "max": 1, "step": 0.1 }}],
    )[0]
    values = opt.grid_values(h)
    assert len(values) == 11
    assert values[0] == 0 and values[-1] == 1
    assert 0.3 in values  # not 0.30000000000000004


def test_grid_values_whole_step_gives_ints():
    h = resolved(
        hp("b", "number", 10, rng(0, 100)),
        values_to_test=[{ "name": "b", "values": { "type": "range", "min": 0, "max": 100, "step": 10 }}],
    )[0]
    values = opt.grid_values(h)
    assert values == list(range(0, 101, 10))
    assert all(isinstance(v, int) for v in values)


def test_grid_values_count_is_evenly_spaced_and_log_is_geometric():
    h = resolved(
        hp("b", "number", 1.0, rng(0)),
        values_to_test=[{ "name": "b", "values": { "type": "range", "min": 0, "max": 1, "count": 3 }}],
    )[0]
    assert opt.grid_values(h) == [0, 0.5, 1]
    h = resolved(
        hp("b", "number", 1.0, rng(0)),
        values_to_test=[{ "name": "b", "values": { "type": "range", "min": 1, "max": 100, "count": 3, "log": True }}],
    )[0]
    assert opt.grid_values(h) == [1, 10, 100]


def test_grid_values_range_without_step_or_count_uses_points_per_range():
    h = resolved(hp("b", "number", 0, rng(0, 1)), points=3)[0]
    assert h["values_to_test"]["count"] == 3
    assert opt.grid_values(h) == [0, 0.5, 1]
    assert len(opt.grid_values(resolved(hp("b", "number", 0, rng(0, 1)))[0])) == 5


def test_grid_values_set_dedupes_and_pinned_hp_uses_promoted_value():
    h = resolved(
        hp("f", "string", "a", values_set("a", "b", "c")),
        values_to_test=[{ "name": "f", "values": values_set("a", "b") }],
    )[0]
    assert opt.grid_values(h) == ["a", "b"]
    pinned = resolved(hp("x", "number", 5, rng(0, 9)), values_to_test=[{ "name": "x", "enabled": False }])[0]
    assert pinned["values_to_test"] is None
    assert opt.grid_values(pinned) == [5]


def test_without_a_benchmark_entry_all_testable_values_are_tested():
    out = resolved(
        hp("f", "string", "a", values_set("a", "b")),
        hp("b", "boolean", True),
        hp("r", "number", 1, rng(0, 4)),
    )
    assert out[0]["values_to_test"] == values_set("a", "b")
    assert out[1]["values_to_test"] == values_set(True, False)
    assert out[2]["values_to_test"]["min"] == 0 and out[2]["values_to_test"]["max"] == 4


def test_optimize_false_pins_every_hyperparameter():
    out = resolved(hp("a", "number", 1, rng(0, 4)), hp("f", "string", "x", values_set("x", "y")), optimize=False)
    assert all(h["values_to_test"] is None for h in out)
    assert opt.count_variants(out) == 1


def test_unbounded_range_needs_a_finite_range_to_test():
    with pytest.raises(ValueError, match="unbounded"):
        resolved(hp("boost", "number", 1, rng(0)))
    with pytest.raises(ValueError, match="unbounded"):
        resolved(hp("boost", "number", 1, rng()), values_to_test=[{ "name": "boost", "enabled": True }])
    out = resolved(
        hp("boost", "number", 1, rng(0)),
        values_to_test=[{ "name": "boost", "values": { "type": "range", "min": 0.5, "max": 8, "log": True }}],
    )
    assert out[0]["values_to_test"]["min"] == 0.5
    # A pinned unbounded hyperparameter is fine
    assert resolved(hp("boost", "number", 1, rng(0)), values_to_test=[{ "name": "boost", "enabled": False }])


def test_values_to_test_must_stay_within_testable_values():
    boost = hp("boost", "number", 1, rng(0, 10))
    for values in (
        { "type": "range", "min": -1, "max": 5 },
        { "type": "range", "min": 1, "max": 11 },
        values_set(1, 11),
    ):
        with pytest.raises(ValueError, match="outside|not one of"):
            resolved(boost, values_to_test=[{ "name": "boost", "values": values }])
    resolved(boost, values_to_test=[{ "name": "boost", "values": values_set(1, 10) }])
    # Against a set of testable values, only a subset of the set is valid
    letters = hp("f", "string", "a", values_set("a", "b", "c"))
    with pytest.raises(ValueError, match="not one of"):
        resolved(letters, values_to_test=[{ "name": "f", "values": values_set("a", "z") }])
    numbers = hp("n", "number", 1, values_set(1, 2, 3))
    with pytest.raises(ValueError, match="set"):
        resolved(numbers, values_to_test=[{ "name": "n", "values": { "type": "range", "min": 1, "max": 2 }}])
    with pytest.raises(ValueError, match="range"):
        resolved(letters, values_to_test=[{ "name": "f", "values": { "type": "range", "min": 1, "max": 2 }}])


def test_strategy_scoped_entry_wins_and_unknown_names_are_ignored():
    h = hp("b", "number", 1, rng(0, 10))
    entries = [
        { "name": "b", "values": values_set(1, 2) },
        { "name": "b", "strategy_id": "s2", "values": values_set(3, 4) },
        { "name": "b", "strategy_id": "s1", "values": values_set(5, 6) },
        { "name": "unknown", "values": values_set(1, 2) },
    ]
    assert resolved(h, values_to_test=entries, strategy_id="s1")[0]["values_to_test"] == values_set(5, 6)
    assert resolved(h, values_to_test=entries, strategy_id="s2")[0]["values_to_test"] == values_set(3, 4)
    assert resolved(h, values_to_test=entries, strategy_id="s3")[0]["values_to_test"] == values_set(1, 2)


####  Variants  ################################################################

def test_no_hyperparameters_is_one_baseline_variant():
    variants = opt.generate_variants([], "fp")
    assert len(variants) == 1
    assert variants[0]["is_baseline"] and variants[0]["values"] == {}
    assert opt.count_variants([]) == 1


def test_grid_is_cartesian_product_with_baseline_first():
    hps = resolved(
        hp("a", "number", 1, rng(1, 3)),
        hp("f", "string", "x", values_set("x", "y")),
        values_to_test=[{ "name": "a", "values": { "type": "range", "min": 1, "max": 3, "step": 1 }}],
    )
    variants = opt.generate_variants(hps, "fp", "grid")
    assert len(variants) == 6 == opt.count_variants(hps, "grid")
    assert variants[0]["is_baseline"] and variants[0]["values"] == { "a": 1, "f": "x" }
    assert sum(v["is_baseline"] for v in variants) == 1
    assert len({ v["variant_id"] for v in variants }) == 6


def test_grid_adds_baseline_when_off_grid():
    hps = resolved(
        hp("a", "number", 7, rng(0, 10)),
        values_to_test=[{ "name": "a", "values": { "type": "range", "min": 0, "max": 10, "step": 5 }}],
    )
    variants = opt.generate_variants(hps, "fp", "grid")
    assert len(variants) == 4 == opt.count_variants(hps, "grid")
    assert variants[0]["values"] == { "a": 7 } and variants[0]["is_baseline"]


def test_grid_over_max_variants_raises(monkeypatch):
    monkeypatch.setattr(opt, "MAX_VARIANTS", 10)
    hps = resolved(
        hp("a", "number", 0, rng(0, 99)),
        values_to_test=[{ "name": "a", "values": { "type": "range", "min": 0, "max": 99, "step": 1 }}],
    )
    with pytest.raises(ValueError):
        opt.generate_variants(hps, "fp", "grid")


def test_random_is_reproducible_and_bounded_by_sample_size():
    hps = resolved(hp("a", "number", 0.5, rng(0, 1)))
    v1 = opt.generate_variants(hps, "fp", "random", 20, "seed")
    v2 = opt.generate_variants(hps, "fp", "random", 20, "seed")
    v3 = opt.generate_variants(hps, "fp", "random", 20, "other")
    assert v1 == v2
    assert v1 != v3
    assert len(v1) == 20 == opt.count_variants(hps, "random", 20)
    assert v1[0]["is_baseline"]
    assert all(0 <= v["values"]["a"] <= 1 for v in v1)


def test_random_is_capped_by_a_finite_space():
    hps = resolved(hp("f", "string", "a", values_set("a", "b", "c")))
    variants = opt.generate_variants(hps, "fp", "random", 50, "s")
    assert len(variants) == 3 == opt.count_variants(hps, "random", 50)


def test_random_log_range_samples_log_uniformly_within_bounds():
    hps = resolved(
        hp("a", "number", 1.0, rng(0)),
        values_to_test=[{ "name": "a", "values": { "type": "range", "min": 0.01, "max": 100, "log": True }}],
    )
    variants = opt.generate_variants(hps, "fp", "random", 200, "s")
    values = [v["values"]["a"] for v in variants]
    assert all(0.01 <= x <= 100 for x in values)
    # Log-uniform sampling puts about half of the samples below 1.
    assert 60 < sum(x < 1 for x in values) < 140


def test_random_range_with_step_snaps_to_the_step():
    hps = resolved(
        hp("n", "number", 5, rng(1, 10)),
        values_to_test=[{ "name": "n", "values": { "type": "range", "min": 1, "max": 10, "step": 1 }}],
    )
    variants = opt.generate_variants(hps, "fp", "random", 10, "s")
    values = [v["values"]["n"] for v in variants]
    assert len(values) == 10 == opt.count_variants(hps, "random", 50)
    assert all(isinstance(x, int) and 1 <= x <= 10 for x in values)
    assert len(set(values)) == 10


def test_random_range_without_step_is_continuous():
    hps = resolved(hp("n", "number", 5, rng(1, 10)))
    values = [v["values"]["n"] for v in opt.generate_variants(hps, "fp", "random", 10, "s")]
    assert any(not isinstance(x, int) for x in values)


def test_variant_values_normalize_whole_floats_to_ints():
    hps = resolved(hp("a", "number", 2.0, rng(0, 4)))
    variants = opt.generate_variants(hps, "fp", "grid")
    assert variants[0]["values"] == { "a": 2 } and isinstance(variants[0]["values"]["a"], int)


def test_variant_id_is_deterministic_and_depends_on_fingerprint_and_values():
    a = opt.variant_id("fp", { "a": 1, "b": 2 })
    assert a == opt.variant_id("fp", { "b": 2, "a": 1 })
    assert a != opt.variant_id("fp2", { "a": 1, "b": 2 })
    assert a != opt.variant_id("fp", { "a": 1, "b": 3 })


####  Split  ###################################################################

def test_split_is_deterministic_disjoint_and_complete():
    ids = [f"s{i}" for i in range(20)]
    t1, h1 = opt.split_scenarios(ids, 0.3, "seed")
    t2, h2 = opt.split_scenarios(list(reversed(ids)), 0.3, "seed")
    assert (t1, h1) == (t2, h2)
    assert len(h1) == 6 and len(t1) == 14
    assert set(t1) | set(h1) == set(ids) and not set(t1) & set(h1)
    assert opt.split_scenarios(ids, 0.3, "other")[1] != h1


def test_split_without_holdout_or_with_one_scenario_is_all_tuning():
    assert opt.split_scenarios(["a", "b"], 0, "s") == (["a", "b"], [])
    assert opt.split_scenarios(["a"], 0.5, "s") == (["a"], [])


def test_split_keeps_at_least_one_tuning_and_one_holdout_scenario():
    t, h = opt.split_scenarios(["a", "b", "c"], 0.9, "s")
    assert len(t) >= 1 and len(h) >= 1
    t, h = opt.split_scenarios(["a", "b", "c", "d"], 0.01, "s")
    assert len(h) == 1


####  Estimates  ###############################################################

def test_estimate_searches_counts_tuning_and_holdout():
    # strategy A: 10 variants, strategy B: 1 variant. 8 tuning, 2 holdout, 2 metrics.
    est = opt.estimate_searches([10, 1], 8, 2, 2)
    assert est["tuning"] == 11 * 8 * 2
    assert est["holdout"] == (2 + 1) * 2 * 2
    assert est["total"] == est["tuning"] + est["holdout"]


def test_estimate_searches_without_holdout():
    est = opt.estimate_searches([3], 5, 0, 4)
    assert est == { "tuning": 60, "holdout": 0, "total": 60 }


def test_estimate_duration_uses_concurrency_batches_and_delay():
    groups = opt.rank_eval_groups([10], 10, 0, 1, batch_size=0)
    assert groups == [{ "strategy_index": 0, "requests": 100, "calls": 1 }]
    est = opt.estimate_duration_ms(groups, [(10, 20)], max_concurrent_searches=10)
    overhead = opt.RUN_OVERHEAD_MS + opt.RANK_EVAL_CALL_OVERHEAD_MS * 1
    assert est == { "low_ms": 100 + overhead, "high_ms": 200 + overhead }  # 10 waves

    groups = opt.rank_eval_groups([10], 10, 0, 1, batch_size=50)
    assert groups[0]["calls"] == 2
    est = opt.estimate_duration_ms(groups, [(10, 20)], 10, batch_size=50, batch_delay_ms=1000)
    overhead = opt.RUN_OVERHEAD_MS + opt.RANK_EVAL_CALL_OVERHEAD_MS * 2
    assert est == { "low_ms": 2 * 5 * 10 + 1000 + overhead, "high_ms": 2 * 5 * 20 + 1000 + overhead }


def test_check_limits(monkeypatch):
    monkeypatch.setattr(opt, "MAX_VARIANTS", 10)
    monkeypatch.setattr(opt, "MAX_SEARCHES", 100)
    assert opt.check_limits([5], 10) == { "errors": [], "warnings": [] }
    assert len(opt.check_limits([11], 10)["errors"]) == 1
    assert len(opt.check_limits([5], 101)["errors"]) == 1
    assert len(opt.check_limits([5], 60)["warnings"]) == 1


####  Aggregation and ranking  #################################################

def search(ndcg, took=None, cov=None):
    return { "metrics": { "ndcg": ndcg }, "took": took, "coverage": cov }


def test_aggregate_searches():
    agg = opt.aggregate_searches([search(0.2, 10, 1.0), search(0.4, 30, 0.5), search(0.9, 20, 0.0)])
    assert agg["n"] == 3
    assert agg["metrics"]["ndcg"]["avg"] == pytest.approx(0.5)
    assert agg["metrics"]["ndcg"]["median"] == 0.4
    assert agg["took"]["median"] == 20
    assert agg["coverage"] == pytest.approx(0.5)


def test_aggregate_without_took_has_no_latency():
    agg = opt.aggregate_searches([search(0.5)])
    assert agg["took"]["median"] is None and agg["took"]["n"] == 0


def test_coverage_of_hits():
    assert opt.coverage([]) is None
    assert opt.coverage([{ "rating": 1 }, { "rating": None }, { "rating": 0 }, {}]) == 0.5


def variant(vid, scores, took=None):
    return { "variant_id": vid, "aggregates": opt.aggregate_searches([search(s, took) for s in scores]) }


OBJ = { "metric": "ndcg", "aggregation": "mean" }


def test_rank_picks_best_mean_and_flags_one_winner():
    ranked = opt.rank_variants([variant("a", [0.5]), variant("b", [0.9]), variant("c", [0.1])], OBJ)
    assert [v["variant_id"] for v in ranked] == ["b", "a", "c"]
    assert [v["is_winner"] for v in ranked] == [True, False, False]
    assert [v["rank"] for v in ranked] == [1, 2, 3]


def test_rank_median_aggregation():
    vs = [variant("a", [0.0, 0.0, 1.0]), variant("b", [0.4, 0.4, 0.4])]
    assert opt.rank_variants(vs, { "metric": "ndcg", "aggregation": "mean" })[0]["variant_id"] == "b"
    assert opt.rank_variants(vs, { "metric": "ndcg", "aggregation": "median" })[0]["variant_id"] == "b"
    vs = [variant("a", [0.1, 0.9, 0.9]), variant("b", [0.5, 0.5, 0.5])]
    assert opt.rank_variants(vs, { "metric": "ndcg", "aggregation": "median" })[0]["variant_id"] == "a"


def test_rank_ties_break_on_lower_latency_then_variant_id():
    vs = [variant("b", [0.5], took=20), variant("c", [0.5], took=10), variant("a", [0.5], took=20)]
    assert [v["variant_id"] for v in opt.rank_variants(vs, OBJ)] == ["c", "a", "b"]


def test_latency_constraint_excludes_winner_but_keeps_variant():
    vs = [variant("fast", [0.5], took=10), variant("slow", [0.9], took=100)]
    ranked = opt.rank_variants(vs, OBJ, { "stat": "median", "max_ms": 50 })
    assert [v["variant_id"] for v in ranked] == ["fast", "slow"]
    assert ranked[0]["is_winner"] and not ranked[1]["is_winner"]
    assert ranked[1]["violates_constraint"]


def test_no_winner_when_every_variant_violates_constraint():
    ranked = opt.rank_variants([variant("a", [0.5], took=100)], OBJ, { "stat": "median", "max_ms": 50 })
    assert not any(v["is_winner"] for v in ranked)


def test_variant_without_latency_passes_constraint():
    ranked = opt.rank_variants([variant("a", [0.5])], OBJ, { "stat": "median", "max_ms": 50 })
    assert ranked[0]["is_winner"]


####  Sensitivity  #############################################################

def test_sensitivity_numeric_and_categorical():
    hps = resolved(
        hp("b", "number", 1, rng(1, 3)),
        hp("f", "string", "x", values_set("x", "y")),
        values_to_test=[{ "name": "b", "values": { "type": "range", "min": 1, "max": 3, "step": 1 }}],
    )
    variants = []
    for b in (1, 2, 3):
        for f in ("x", "y"):
            variants.append({ "values": { "b": b, "f": f }, "score": b / 10 + (0.01 if f == "y" else 0) })
    out = {s["name"]: s for s in opt.sensitivity(variants, hps)}
    assert out["b"]["kind"] == "numeric"
    assert [p["value"] for p in out["b"]["points"]] == [1, 2, 3]
    assert out["b"]["spread"] == pytest.approx(0.2)
    assert out["f"]["kind"] == "categorical"
    assert out["f"]["spread"] == pytest.approx(0.01)
    assert out["b"]["spread"] > out["f"]["spread"]


def test_sensitivity_bins_many_numeric_values():
    hps = resolved(hp("a", "number", 0.5, rng(0, 1)))
    variants = [{ "values": { "a": i / 99 }, "score": i / 99 } for i in range(100)]
    out = opt.sensitivity(variants, hps, max_points=5)[0]
    assert out["binned"] and len(out["points"]) == 5
    means = [p["mean"] for p in out["points"]]
    assert means == sorted(means)
