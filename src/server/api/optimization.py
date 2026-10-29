# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""Hyperparameter optimization core.

Pure functions with no Elasticsearch I/O: values-to-test resolution, variant
generation, variant IDs, scenario splits, cost estimates, winner ranking, and
sensitivity analysis. `runs.py` executes the plan these functions produce.

Terminology:
  * Hyperparameter: a user-defined strategy parameter ({{hp.<name>}}).
  * Promoted value: the value a strategy uses for a hyperparameter today.
  * Valid testable values: the values a strategy allows a benchmark to test.
  * Values to test: the values a benchmark tests (range or set).
  * Variant: a strategy with one combination of hyperparameter values bound.
  * Baseline: the variant that uses every promoted value.
"""

# Standard packages
import itertools
import math
import os
import random
import statistics
from typing import Any, Dict, List, Optional, Tuple

# App packages
from .. import utils
from ..models.hyperparameters import (
    Hyperparameter, RE_UNSAFE_STRING, ValuesToTest, check_value_type, value_is_testable,
)

# Configurable limits. Grid search grows multiplicatively, so both the number
# of variants per strategy and the total number of searches are capped.
MAX_VARIANTS = int(os.getenv("HPO_MAX_VARIANTS", "1000"))
MAX_SEARCHES = int(os.getenv("HPO_MAX_SEARCHES", "200000"))

# Holdout sets smaller than this produce unstable scores.
MIN_STABLE_HOLDOUT_SCENARIOS = 30
# Judgement coverage below this makes a winner's score unreliable.
LOW_COVERAGE_THRESHOLD = 0.5

# Default `max_concurrent_searches` of the _rank_eval API in Elasticsearch.
DEFAULT_MAX_CONCURRENT_SEARCHES = 10

# Time a run spends outside of the searches, which a duration estimate adds to
# the search time: a fixed cost and a cost per _rank_eval call.
RUN_OVERHEAD_MS = 2000
RANK_EVAL_CALL_OVERHEAD_MS = 50

# Default number of grid points of a range without a `step` or `count`.
DEFAULT_POINTS_PER_RANGE = 5


####  Values to test  ##########################################################

def _normalize(type_: str, value: Any, log: bool = False) -> Any:
    if type_ == "number" and log:
        return utils.normalize_hyperparameter_value(type_, float(f"{float(value):.6g}"))
    return utils.normalize_hyperparameter_value(type_, value)


def _dedupe(values: List[Any]) -> List[Any]:
    seen = set()
    out = []
    for v in values:
        key = utils.serialize(v)
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def _check_within(name: str, hp: Dict[str, Any], values: Dict[str, Any]):
    """Check that values to test are within a hyperparameter's valid testable
    values. Raises ValueError if they aren't."""
    testable = hp["testable_values"]
    where = f"values to test for '{name}'"
    if values["type"] == "set":
        for v in values["values"]:
            if not value_is_testable(hp["type"], v, testable):
                raise ValueError(f"{where} include {v!r}, which is not one of the valid testable values")
        return
    if hp["type"] != "number":
        raise ValueError(f"{where} can't be a range because '{name}' is a {hp['type']}")
    if testable["type"] == "set":
        raise ValueError(f"{where} can't be a range because the valid testable values are a set")
    for bound in ("min", "max"):
        if not value_is_testable(hp["type"], values[bound], testable):
            raise ValueError(
                f"{where} have a {bound} of {values[bound]!r}, "
                "which is outside the valid testable values"
            )


def _derive_values(hp: Dict[str, Any], points_per_range: int) -> Dict[str, Any]:
    """The values to test of a hyperparameter with no benchmark entry: all of
    its valid testable values. A range needs finite bounds."""
    testable = hp["testable_values"]
    if testable["type"] == "set":
        return { "type": "set", "values": list(testable["values"]) }
    if testable.get("min") is None or testable.get("max") is None:
        raise ValueError(
            f"the valid testable values of '{hp['name']}' are unbounded. "
            "Set a finite range to test in the benchmark's values_to_test, "
            "or turn off testing of this hyperparameter."
        )
    return { "type": "range", "min": testable["min"], "max": testable["max"], "log": False }


def _check_override(name: str, type_: str, value: Any) -> Any:
    if not check_value_type(type_, value):
        raise ValueError(f"the value of hyperparameter '{name}' must be a valid {type_}")
    if isinstance(value, str) and RE_UNSAFE_STRING.search(value):
        raise ValueError(
            f"the value of hyperparameter '{name}' must not contain quotes, backslashes, or control characters"
        )
    return value


def resolve_hyperparameters(
        hyperparameters: Optional[List[Dict[str, Any]]],
        values_to_test: Optional[List[Dict[str, Any]]] = None,
        strategy_id: Optional[str] = None,
        points_per_range: int = DEFAULT_POINTS_PER_RANGE,
        optimize: bool = True,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
    """Resolve the effective hyperparameters of a strategy for a benchmark.

    With `optimize` false (a benchmark without hyperparameter optimization),
    every hyperparameter keeps its promoted value, so the strategy is a single
    baseline variant.

    Otherwise each hyperparameter tests either the benchmark's values for its
    name (an entry scoped to this strategy wins over one for every strategy),
    or all of its valid testable values. Entries for names the strategy
    doesn't define are ignored. Entries that fall outside the valid testable
    values, and unbounded ranges without a finite range to test, raise
    ValueError.

    `overrides` replaces the promoted values by name, for an ad hoc test of one
    set of values. An override must fit the hyperparameter's type, but it
    needn't be one of the valid testable values. Use it with `optimize` false.

    Returns a list of {name, type, promoted_value, testable_values,
    values_to_test} dicts. `values_to_test` is None when the hyperparameter
    keeps its promoted value, and a range gets a `step` or a `count`.
    """
    entries: Dict[Tuple[Optional[str], str], ValuesToTest] = {}
    for raw in (values_to_test or []):
        entry = ValuesToTest.model_validate(raw)
        entries[(entry.strategy_id, entry.name)] = entry
    resolved = []
    for raw in (hyperparameters or []):
        hp = Hyperparameter.model_validate(raw).model_dump()
        name = hp["name"]
        if overrides and name in overrides:
            hp["promoted_value"] = _check_override(name, hp["type"], overrides[name])
        entry = entries.get((strategy_id, name)) or entries.get((None, name))
        if not optimize or (entry is not None and not entry.enabled):
            hp["values_to_test"] = None
        elif entry is not None and entry.values is not None:
            values = entry.values.model_dump()
            _check_within(name, hp, values)
            hp["values_to_test"] = values
        else:
            hp["values_to_test"] = _derive_values(hp, points_per_range)
        values = hp["values_to_test"]
        if values and values["type"] == "range":
            values.setdefault("log", False)
            if values.get("step") is None and values.get("count") is None:
                values["count"] = points_per_range
        resolved.append(hp)
    return resolved


def grid_values(hp: Dict[str, Any]) -> List[Any]:
    """Every value of a hyperparameter's values to test, for grid search.

    A hyperparameter that keeps its promoted value contributes only that value.
    """
    values = hp.get("values_to_test")
    type_ = hp["type"]
    if not values:
        return [_normalize(type_, hp["promoted_value"])]
    if values["type"] == "set":
        return _dedupe([_normalize(type_, v) for v in values["values"]])
    lo, hi = values["min"], values["max"]
    log = bool(values.get("log"))
    step, count = values.get("step"), values.get("count") or DEFAULT_POINTS_PER_RANGE
    if step is not None:
        n = int(math.floor((hi - lo) / step + 1e-9)) + 1
        points = [lo + i * step for i in range(n)]
    elif count == 1 or lo == hi:
        points = [lo]
    elif log:
        points = [lo * (hi / lo) ** (i / (count - 1)) for i in range(count)]
    else:
        points = [lo + (hi - lo) * i / (count - 1) for i in range(count)]
    return _dedupe([_normalize(type_, v, log) for v in points])


def sample_value(hp: Dict[str, Any], rng: random.Random) -> Any:
    """Sample one value from a hyperparameter's values to test, for random
    search. Ranges are sampled continuously (log-uniformly for log ranges) and
    snapped to the `step` if there is one."""
    values = hp.get("values_to_test")
    type_ = hp["type"]
    if not values:
        return _normalize(type_, hp["promoted_value"])
    if values["type"] == "set":
        return _normalize(type_, rng.choice(values["values"]))
    lo, hi = values["min"], values["max"]
    log = bool(values.get("log"))
    value = math.exp(rng.uniform(math.log(lo), math.log(hi))) if log else rng.uniform(lo, hi)
    step = values.get("step")
    if step is not None:
        last = int(math.floor((hi - lo) / step + 1e-9))
        value = lo + min(last, max(0, int(round((value - lo) / step)))) * step
    return _normalize(type_, value, log)


def _finite_size(hp: Dict[str, Any]) -> float:
    """Number of distinct values to test (infinite for a range without a step)."""
    values = hp.get("values_to_test")
    if not values:
        return 1
    if values["type"] == "set":
        return len(_dedupe([_normalize(hp["type"], v) for v in values["values"]]))
    step = values.get("step")
    if step is not None:
        return int(math.floor((values["max"] - values["min"]) / step + 1e-9)) + 1
    return math.inf


def _promoted_values(hyperparameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    return { hp["name"]: _normalize(hp["type"], hp["promoted_value"]) for hp in hyperparameters }


def variant_id(template_fingerprint: str, values: Dict[str, Any]) -> str:
    """Deterministic variant ID from the template fingerprint and the sorted
    hyperparameter values. Stable across runs for identical templates/values."""
    return utils.unique_id([template_fingerprint, sorted(values.items())])


def count_variants(
        hyperparameters: List[Dict[str, Any]],
        algorithm: str = "grid",
        sample_size: int = 50,
    ) -> int:
    """Number of variants a search produces, without materializing them.

    The baseline variant is always included. For grid search, it adds one
    variant when the promoted combination is outside the grid. For random
    search, the baseline counts toward `sample_size`.
    """
    if not hyperparameters:
        return 1
    if algorithm == "grid":
        grids = [grid_values(hp) for hp in hyperparameters]
        total = math.prod(len(g) for g in grids)
        promoted = _promoted_values(hyperparameters)
        in_grid = all(
            utils.serialize(promoted[hp["name"]]) in { utils.serialize(v) for v in grid }
            for hp, grid in zip(hyperparameters, grids)
        )
        return total if in_grid else total + 1
    size = math.prod(_finite_size(hp) for hp in hyperparameters)
    return int(min(sample_size, size))


def generate_variants(
        hyperparameters: List[Dict[str, Any]],
        template_fingerprint: str,
        algorithm: str = "grid",
        sample_size: int = 50,
        seed: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
    """Generate the variants of a strategy: [{variant_id, values, is_baseline}].

    The baseline variant is always included. Grid search yields the Cartesian
    product of the values to test. Random search yields `sample_size` distinct
    variants (including the baseline) sampled with a seeded generator, so the
    same seed and template reproduce the same variants. A strategy without
    hyperparameters yields a single baseline variant.
    """
    promoted = _promoted_values(hyperparameters)
    baseline_id = variant_id(template_fingerprint, promoted)
    variants = { baseline_id: { "variant_id": baseline_id, "values": promoted, "is_baseline": True }}
    names = [hp["name"] for hp in hyperparameters]

    if not hyperparameters:
        return list(variants.values())

    if algorithm == "grid":
        count = count_variants(hyperparameters, "grid")
        if count > MAX_VARIANTS:
            raise ValueError(
                f"grid search would produce {count} variants, above the maximum of {MAX_VARIANTS}. "
                "Narrow the values to test or use random search."
            )
        grids = [grid_values(hp) for hp in hyperparameters]
        ordered = []
        for combo in itertools.product(*grids):
            values = dict(zip(names, combo))
            vid = variant_id(template_fingerprint, values)
            if vid == baseline_id:
                continue
            ordered.append({ "variant_id": vid, "values": values, "is_baseline": False })
        # The baseline variant comes first, followed by the grid in product order.
        return list(variants.values()) + ordered

    if sample_size > MAX_VARIANTS:
        raise ValueError(
            f"random search would sample {sample_size} variants, above the maximum of {MAX_VARIANTS}."
        )
    target = int(min(sample_size, math.prod(_finite_size(hp) for hp in hyperparameters)))
    rng = random.Random(utils.fingerprint([seed or "", template_fingerprint]))
    attempts = 0
    while len(variants) < target and attempts < max(100, target * 50):
        attempts += 1
        values = { hp["name"]: sample_value(hp, rng) for hp in hyperparameters }
        vid = variant_id(template_fingerprint, values)
        if vid not in variants:
            variants[vid] = { "variant_id": vid, "values": values, "is_baseline": False }
    return list(variants.values())


####  Scenario split  ##########################################################

def split_scenarios(
        scenario_ids: List[str],
        ratio: float = 0,
        seed: Optional[str] = None,
    ) -> Tuple[List[str], List[str]]:
    """Split scenarios into a (tuning, holdout) set with a seeded shuffle.

    With a ratio of 0, every scenario is a tuning scenario. Otherwise the
    holdout gets round(n * ratio) scenarios (at least 1), leaving at least 1
    for tuning. The same ids, ratio, and seed always give the same split.
    """
    ids = sorted(set(scenario_ids))
    if ratio <= 0 or len(ids) < 2:
        return ids, []
    n_holdout = min(len(ids) - 1, max(1, int(round(len(ids) * ratio))))
    shuffled = list(ids)
    random.Random(utils.fingerprint([seed or "", ids])).shuffle(shuffled)
    holdout = sorted(shuffled[:n_holdout])
    holdout_set = set(holdout)
    tuning = [i for i in ids if i not in holdout_set]
    return tuning, holdout


####  Cost estimates  ##########################################################

def estimate_searches(
        variant_counts: List[int],
        n_tuning: int,
        n_holdout: int,
        n_metrics: int,
    ) -> Dict[str, int]:
    """Number of individual searches (not parent _rank_eval calls) of a run:

      tuning  = sum(variants_s) x tuning scenarios x metrics
      holdout = sum(1 or 2 per strategy) x holdout scenarios x metrics

    The holdout phase tests the winning and the baseline variant of each
    strategy. The count is an upper bound when the winner is the baseline.
    """
    tuning = sum(variant_counts) * n_tuning * n_metrics
    holdout = 0
    if n_holdout:
        holdout = sum(2 if c > 1 else 1 for c in variant_counts) * n_holdout * n_metrics
    return { "tuning": tuning, "holdout": holdout, "total": tuning + holdout }


def rank_eval_groups(
        variant_counts: List[int],
        n_tuning: int,
        n_holdout: int,
        n_metrics: int,
        batch_size: int = 0,
    ) -> List[Dict[str, int]]:
    """The _rank_eval calls of a run, grouped per (strategy, phase, metric).
    Returns [{strategy_index, requests, calls}] where `requests` is the number
    of searches in the group and `calls` the number of _rank_eval calls after
    batching."""
    groups = []
    for i, c in enumerate(variant_counts):
        phases = [c * n_tuning]
        if n_holdout:
            phases.append((2 if c > 1 else 1) * n_holdout)
        for requests in phases:
            if not requests:
                continue
            calls = math.ceil(requests / batch_size) if batch_size and batch_size > 0 else 1
            for _ in range(n_metrics):
                groups.append({ "strategy_index": i, "requests": requests, "calls": calls })
    return groups


def estimate_duration_ms(
        groups: List[Dict[str, int]],
        latency_ms: List[Tuple[float, float]],
        max_concurrent_searches: int = DEFAULT_MAX_CONCURRENT_SEARCHES,
        batch_size: int = 0,
        batch_delay_ms: float = 0,
    ) -> Dict[str, float]:
    """Extrapolate a duration range from per-search latency probes.

    Args:
        groups: output of rank_eval_groups.
        latency_ms: per-strategy (low, high) per-search latency, indexed by
            `strategy_index` (e.g. the p25 and p75 of the probe's wall times).
        max_concurrent_searches: concurrency within one _rank_eval call.
        batch_size: max requests per _rank_eval call (0 for no limit).
        batch_delay_ms: delay between the batches of one group.

    Returns {"low_ms", "high_ms"}. Calls run one after another, and the
    searches within a call run `max_concurrent_searches` at a time. The range
    includes the run's overhead outside of the searches (reading the assets,
    and writing the results), as a fixed cost plus a cost per _rank_eval call.
    """
    mcs = max(1, max_concurrent_searches or DEFAULT_MAX_CONCURRENT_SEARCHES)
    overhead = RUN_OVERHEAD_MS + RANK_EVAL_CALL_OVERHEAD_MS * sum(g["calls"] for g in groups)
    totals = [float(overhead), float(overhead)]
    for g in groups:
        requests, calls = g["requests"], g["calls"]
        per_call = math.ceil(requests / calls) if calls else requests
        waves = math.ceil(per_call / mcs)
        low, high = latency_ms[g["strategy_index"]]
        delay = batch_delay_ms * max(0, calls - 1)
        # Searches across the calls of a group are equally sized, so the waves
        # scale with the number of calls.
        totals[0] += calls * waves * low + delay
        totals[1] += calls * waves * high + delay
    return { "low_ms": totals[0], "high_ms": totals[1] }


def check_limits(variant_counts: List[int], total_searches: int) -> Dict[str, List[str]]:
    """Check run size against the configured maximums. Returns
    {"errors": [...], "warnings": [...]}. Errors must block a run."""
    errors, warnings = [], []
    worst = max(variant_counts) if variant_counts else 0
    if worst > MAX_VARIANTS:
        errors.append(f"A strategy has {worst} variants, above the maximum of {MAX_VARIANTS}.")
    if total_searches > MAX_SEARCHES:
        errors.append(f"The run would make {total_searches} searches, above the maximum of {MAX_SEARCHES}.")
    elif total_searches > MAX_SEARCHES * 0.5:
        warnings.append(f"The run would make {total_searches} searches, over half of the maximum of {MAX_SEARCHES}.")
    return { "errors": errors, "warnings": warnings }


####  Aggregation and ranking  #################################################

def percentile(values: List[float], q: float) -> Optional[float]:
    """Linear-interpolated percentile (q in 0..100). None for no values."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * q / 100.0
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo))


def coverage(hits: List[Dict[str, Any]]) -> Optional[float]:
    """Share of returned hits that have a rating. None when there are no hits."""
    if not hits:
        return None
    return sum(1 for h in hits if h.get("rating") is not None) / len(hits)


def aggregate_searches(searches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate the searches (one per scenario) of a variant.

    Returns {"n", "metrics": {name: {avg, median, min, max}},
    "took": {avg, median, p90, n}, "coverage": avg or None}.
    """
    metric_values: Dict[str, List[float]] = {}
    took_values: List[float] = []
    coverages: List[float] = []
    for s in searches:
        for name, value in (s.get("metrics") or {}).items():
            if value is not None:
                metric_values.setdefault(name, []).append(value)
        if s.get("took") is not None:
            took_values.append(s["took"])
        if s.get("coverage") is not None:
            coverages.append(s["coverage"])
    metrics = {
        name: {
            "avg": sum(v) / len(v), "median": statistics.median(v), "min": min(v), "max": max(v),
        }
        for name, v in metric_values.items() if v
    }
    took = {
        "avg": sum(took_values) / len(took_values) if took_values else None,
        "median": percentile(took_values, 50),
        "p90": percentile(took_values, 90),
        "n": len(took_values),
    }
    return {
        "n": len(searches),
        "metrics": metrics,
        "took": took,
        "coverage": sum(coverages) / len(coverages) if coverages else None,
    }


def objective_score(aggregates: Dict[str, Any], objective: Dict[str, Any]) -> Optional[float]:
    """The objective's score of a variant's aggregates (None when missing)."""
    metric = (aggregates.get("metrics") or {}).get(objective["metric"])
    if not metric:
        return None
    return metric["median"] if objective.get("aggregation") == "median" else metric["avg"]


def violates_latency(aggregates: Dict[str, Any], constraint: Optional[Dict[str, Any]]) -> bool:
    """Whether a variant breaks the latency constraint. A variant without
    latency data (Elasticsearch before 9.6.0) can't be judged, so it passes."""
    if not constraint:
        return False
    stat = { "mean": "avg", "median": "median", "p90": "p90" }[constraint.get("stat", "median")]
    value = (aggregates.get("took") or {}).get(stat)
    return value is not None and value > constraint["max_ms"]


def rank_variants(
        variants: List[Dict[str, Any]],
        objective: Dict[str, Any],
        constraint: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
    """Rank variants by the objective, best first.

    Each input variant needs `variant_id` and `aggregates`. Ties break on lower
    median latency, then on variant_id, so the order is deterministic. Variants
    that violate the latency constraint sort after all that satisfy it and are
    flagged `violates_constraint`, so they can't win but still appear.

    Returns copies of the variants with `score`, `violates_constraint`, `rank`
    (1-based), and `is_winner` (True for the first variant that satisfies the
    constraint and has a score).
    """
    ranked = []
    for v in variants:
        aggregates = v.get("aggregates") or {}
        score = objective_score(aggregates, objective)
        ranked.append({
            **v,
            "score": score,
            "violates_constraint": violates_latency(aggregates, constraint),
        })
    def key(v):
        median_took = ((v.get("aggregates") or {}).get("took") or {}).get("median")
        return (
            v["violates_constraint"],
            v["score"] is None,
            -(v["score"] if v["score"] is not None else 0),
            median_took if median_took is not None else math.inf,
            v["variant_id"],
        )
    ranked.sort(key=key)
    winner_assigned = False
    for i, v in enumerate(ranked):
        v["rank"] = i + 1
        eligible = not v["violates_constraint"] and v["score"] is not None
        v["is_winner"] = eligible and not winner_assigned
        winner_assigned = winner_assigned or v["is_winner"]
    return ranked


def sensitivity(
        variants: List[Dict[str, Any]],
        hyperparameters: List[Dict[str, Any]],
        max_points: int = 10,
    ) -> List[Dict[str, Any]]:
    """Per-hyperparameter sensitivity of the objective.

    Each input variant needs `values` and `score`. For each hyperparameter,
    groups variants by value (numeric values with more than `max_points`
    distinct values are binned) and reports the mean and best score per group.
    `spread` is the gap between the best and worst group mean. A small spread
    means the hyperparameter barely matters. This is a marginal view, so it
    averages over all other hyperparameters.
    """
    scored = [v for v in variants if v.get("score") is not None]
    out = []
    for hp in hyperparameters:
        name = hp["name"]
        numeric = hp["type"] == "number"
        groups: Dict[str, Dict[str, Any]] = {}
        distinct = sorted({ v["values"][name] for v in scored if name in v["values"] }) if numeric else []
        binned = numeric and not _is_set(hp) and len(distinct) > max_points
        if binned:
            lo, hi = distinct[0], distinct[-1]
            width = (hi - lo) / max_points or 1
        for v in scored:
            if name not in v["values"]:
                continue
            value = v["values"][name]
            if binned:
                idx = min(max_points - 1, int((value - lo) / width))
                key = idx
                label = lo + width * (idx + 0.5)
            else:
                key = utils.serialize(value)
                label = value
            g = groups.setdefault(key, { "value": label, "scores": [] })
            g["scores"].append(v["score"])
        points = [
            {
                "value": g["value"], "n": len(g["scores"]),
                "mean": sum(g["scores"]) / len(g["scores"]), "best": max(g["scores"]),
            }
            for g in groups.values()
        ]
        points.sort(key=lambda p: (p["value"] is None, p["value"] if numeric else utils.serialize(p["value"])))
        means = [p["mean"] for p in points]
        out.append({
            "name": name,
            "type": hp["type"],
            "kind": "numeric" if numeric and not _is_set(hp) else "categorical",
            "binned": bool(binned),
            "points": points,
            "spread": (max(means) - min(means)) if means else 0.0,
        })
    return out


def _is_set(hp: Dict[str, Any]) -> bool:
    return bool(hp.get("values_to_test")) and hp["values_to_test"]["type"] == "set"
