# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Convenience functions for the code execution sandbox.

These provide lightweight access to common data without the full ES response overhead.
Extracted from fastmcp_resources.py for use in the code execution sandbox.
"""

from typing import Any, Dict

from . import api
from .client import es


# Workspaces

def workspaces_list() -> Dict[str, Any]:
    """
    Lightweight list of all workspaces.
    Returns {count, workspaces: [{_id, name, index_pattern, params, rating_scale, tags}, ...]}
    """
    es_response = api.workspaces.search(size=1000)
    hits = es_response.body.get("hits", {}).get("hits", [])
    workspaces = []
    for hit in hits:
        source = hit.get("_source", {})
        workspaces.append({
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "index_pattern": source.get("index_pattern"),
            "params": source.get("params", []),
            "rating_scale": source.get("rating_scale"),
            "tags": source.get("tags", []),
        })
    result = {"count": len(workspaces), "workspaces": workspaces}
    if len(workspaces) == 1000:
        result["_warning"] = "Results truncated at 1000."
    return result


# Displays

def displays_list(workspace_id: str) -> Dict[str, Any]:
    """
    Lightweight list of displays in a workspace.
    Returns {count, displays: [{_id, index_pattern, template}, ...]}
    """
    es_response = api.displays.search(workspace_id=workspace_id, size=1000)
    hits = es_response.body.get("hits", {}).get("hits", [])
    displays = []
    for hit in hits:
        source = hit.get("_source", {})
        displays.append({
            "_id": hit.get("_id"),
            "index_pattern": source.get("index_pattern"),
            "template": source.get("template"),
        })
    result = {"workspace_id": workspace_id, "count": len(displays), "displays": displays}
    if len(displays) == 1000:
        result["_warning"] = "Results truncated at 1000."
    return result


# Scenarios

def scenarios_list(workspace_id: str) -> Dict[str, Any]:
    """
    Lightweight list of scenarios in a workspace.
    Returns {count, scenarios: [{_id, name, values, tags}, ...]}
    """
    es_response = api.scenarios.search(workspace_id=workspace_id, size=1000)
    hits = es_response.body.get("hits", {}).get("hits", [])
    scenarios = []
    for hit in hits:
        source = hit.get("_source", {})
        scenarios.append({
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "values": source.get("values", {}),
            "tags": source.get("tags", []),
        })
    result = {"workspace_id": workspace_id, "count": len(scenarios), "scenarios": scenarios}
    if len(scenarios) == 1000:
        result["_warning"] = "Results truncated at 1000."
    return result


def scenarios_by_tag(workspace_id: str, tag: str) -> Dict[str, Any]:
    """
    Get scenarios filtered by a specific tag.
    Returns {workspace_id, tag, count, scenarios: [{_id, name, values, tags}, ...]}
    """
    es_response = api.scenarios.search(
        workspace_id=workspace_id,
        filters=[{"term": {"tags": tag}}],
        size=1000
    )
    hits = es_response.body.get("hits", {}).get("hits", [])
    scenarios = []
    for hit in hits:
        source = hit.get("_source", {})
        scenarios.append({
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "values": source.get("values", {}),
            "tags": source.get("tags", []),
        })
    return {
        "workspace_id": workspace_id,
        "tag": tag,
        "count": len(scenarios),
        "scenarios": scenarios,
    }


# Strategies

def strategies_list(workspace_id: str) -> Dict[str, Any]:
    """
    Lightweight list of strategies in a workspace.
    Returns {count, strategies: [{_id, name, tags}, ...]}
    """
    es_response = api.strategies.search(workspace_id=workspace_id, size=1000)
    hits = es_response.body.get("hits", {}).get("hits", [])
    strategies = []
    for hit in hits:
        source = hit.get("_source", {})
        strategies.append({
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "tags": source.get("tags", []),
        })
    result = {"workspace_id": workspace_id, "count": len(strategies), "strategies": strategies}
    if len(strategies) == 1000:
        result["_warning"] = "Results truncated at 1000."
    return result


def strategies_by_tag(workspace_id: str, tag: str) -> Dict[str, Any]:
    """
    Get strategies filtered by a specific tag.
    Returns {workspace_id, tag, count, strategies: [{_id, name, tags}, ...]}
    """
    es_response = api.strategies.search(
        workspace_id=workspace_id,
        filters=[{"term": {"tags": tag}}],
        size=1000
    )
    hits = es_response.body.get("hits", {}).get("hits", [])
    strategies = []
    for hit in hits:
        source = hit.get("_source", {})
        strategies.append({
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "tags": source.get("tags", []),
        })
    return {
        "workspace_id": workspace_id,
        "tag": tag,
        "count": len(strategies),
        "strategies": strategies,
    }


def strategy_template(_id: str) -> Dict[str, Any]:
    """
    Get just the template source for a specific strategy.
    Returns {_id, workspace_id, name, template: {lang, source}}
    """
    es_response = api.strategies.get(_id)
    source = es_response.body.get("_source", {})
    return {
        "_id": _id,
        "workspace_id": source.get("workspace_id"),
        "name": source.get("name"),
        "template": source.get("template", {}),
    }


# Benchmarks

def benchmarks_list(workspace_id: str) -> Dict[str, Any]:
    """
    Lightweight list of benchmarks in a workspace.
    Returns {count, benchmarks: [{_id, name, description, tags}, ...]}
    """
    es_response = api.benchmarks.search(workspace_id=workspace_id, size=1000)
    hits = es_response.body.get("hits", {}).get("hits", [])
    benchmarks = []
    for hit in hits:
        source = hit.get("_source", {})
        benchmarks.append({
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "description": source.get("description"),
            "tags": source.get("tags", []),
        })
    result = {"workspace_id": workspace_id, "count": len(benchmarks), "benchmarks": benchmarks}
    if len(benchmarks) == 1000:
        result["_warning"] = "Results truncated at 1000."
    return result


def benchmark_task(_id: str) -> Dict[str, Any]:
    """
    Get the task definition for a specific benchmark.
    Returns {_id, workspace_id, name, task: {metrics, k, strategies, scenarios}}
    """
    es_response = api.benchmarks.get(_id)
    source = es_response.body.get("_source", {})
    return {
        "_id": _id,
        "workspace_id": source.get("workspace_id"),
        "name": source.get("name"),
        "task": source.get("task", {}),
    }


# Evaluations

def evaluations_list(workspace_id: str) -> Dict[str, Any]:
    """
    Lightweight list of evaluations in a workspace.
    Returns {count, evaluations: [{_id, benchmark_id, status, started_at, took}, ...]}
    """
    body = {
        "query": {"bool": {"filter": [{"term": {"workspace_id": workspace_id}}]}},
        "size": 1000,
        "_source": ["@meta.status", "@meta.started_at", "benchmark_id", "took"],
    }
    es_response = es("studio").search(index="esrs-evaluations", body=body)
    hits = es_response.body.get("hits", {}).get("hits", [])
    evaluations = []
    for hit in hits:
        source = hit.get("_source", {})
        meta = source.get("@meta", {})
        evaluations.append({
            "_id": hit.get("_id"),
            "benchmark_id": source.get("benchmark_id"),
            "status": meta.get("status"),
            "started_at": meta.get("started_at"),
            "took": source.get("took"),
        })
    result = {"workspace_id": workspace_id, "count": len(evaluations), "evaluations": evaluations}
    if len(evaluations) == 1000:
        result["_warning"] = "Results truncated at 1000."
    return result


def evaluation_status(_id: str) -> Dict[str, Any]:
    """
    Get just the status and metadata of an evaluation.
    Returns {_id, workspace_id, benchmark_id, status, started_at, started_by, took, error}
    """
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    meta = source.get("@meta", {})
    return {
        "_id": _id,
        "workspace_id": source.get("workspace_id"),
        "benchmark_id": source.get("benchmark_id"),
        "status": meta.get("status"),
        "started_at": meta.get("started_at"),
        "started_by": meta.get("started_by"),
        "took": source.get("took"),
        "error": source.get("error"),
    }


def evaluation_summary(_id: str) -> Dict[str, Any]:
    """
    Get just the summary metrics of a completed evaluation.
    Returns {_id, workspace_id, benchmark_id, status, took, summary} where summary contains metrics by strategy_id/tag.
    Much smaller than the full evaluation (2KB vs 100KB).
    """
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    return {
        "_id": _id,
        "workspace_id": source.get("workspace_id"),
        "benchmark_id": source.get("benchmark_id"),
        "status": source.get("@meta", {}).get("status"),
        "took": source.get("took"),
        "summary": source.get("summary", {}),
    }


def latest_evaluation_summary(workspace_id: str) -> Dict[str, Any]:
    """
    Get the summary of the most recent completed evaluation in a workspace.
    Returns {_id, status, took, summary} or {error} if none found.
    """
    body = {
        "query": {"bool": {"filter": [
            {"term": {"workspace_id": workspace_id}},
            {"term": {"@meta.status": "completed"}},
        ]}},
        "size": 1,
        "sort": [{"@meta.started_at": {"order": "desc"}}],
        "_source": ["@meta", "took", "benchmark_id", "summary"],
    }
    es_response = es("studio").search(index="esrs-evaluations", body=body)
    hits = es_response.body.get("hits", {}).get("hits", [])
    if not hits:
        return {"error": "No completed evaluations found", "workspace_id": workspace_id}
    hit = hits[0]
    source = hit.get("_source", {})
    return {
        "_id": hit.get("_id"),
        "benchmark_id": source.get("benchmark_id"),
        "status": source.get("@meta", {}).get("status"),
        "took": source.get("took"),
        "summary": source.get("summary", {}),
    }


def evaluation_task(_id: str) -> Dict[str, Any]:
    """
    Get the task definition of an evaluation.
    Returns {_id, workspace_id, benchmark_id, task, strategy_id, scenario_id}
    """
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    return {
        "_id": _id,
        "workspace_id": source.get("workspace_id"),
        "benchmark_id": source.get("benchmark_id"),
        "task": source.get("task", {}),
        "strategy_id": source.get("strategy_id", []),
        "scenario_id": source.get("scenario_id", []),
    }


def evaluation_results_for_strategy(_id: str, strategy_id: str) -> Dict[str, Any]:
    """
    Get results for a specific strategy from an evaluation.
    Returns {_id, workspace_id, benchmark_id, strategy_id, searches, failures} or {error} if not found.
    Much smaller than full evaluation.
    """
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    results = source.get("results", [])

    strategy_results = None
    for r in results:
        if r.get("strategy_id") == strategy_id:
            strategy_results = r
            break

    if strategy_results is None:
        return {
            "_id": _id,
            "workspace_id": source.get("workspace_id"),
            "benchmark_id": source.get("benchmark_id"),
            "strategy_id": strategy_id,
            "error": f"Strategy {strategy_id} not found in evaluation results",
            "available_strategies": [r.get("strategy_id") for r in results]
        }

    return {
        "_id": _id,
        "workspace_id": source.get("workspace_id"),
        "benchmark_id": source.get("benchmark_id"),
        "strategy_id": strategy_id,
        "searches": strategy_results.get("searches", []),
        "failures": strategy_results.get("failures", []),
    }


def evaluation_unrated_docs(_id: str) -> Dict[str, Any]:
    """
    Get the list of unrated documents found during an evaluation.
    Useful for identifying which documents need judgements.
    Returns {_id, workspace_id, benchmark_id, unrated_docs: [...]}
    """
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    return {
        "_id": _id,
        "workspace_id": source.get("workspace_id"),
        "benchmark_id": source.get("benchmark_id"),
        "unrated_docs": source.get("unrated_docs", []),
    }


def evaluation_strategies(_id: str) -> Dict[str, Any]:
    """
    Get list of strategy IDs that were evaluated, with their summary metrics.
    For running/failed evaluations without summary, falls back to task or results.
    Returns {_id, workspace_id, benchmark_id, strategies: [{strategy_id, metrics}, ...]}
    """
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    summary = source.get("summary", {})
    strategy_summaries = summary.get("strategy_id", {})

    strategies = []

    if strategy_summaries:
        # Completed evaluation with summary metrics
        for strategy_id, metrics in strategy_summaries.items():
            total = metrics.get("_total", {}).get("metrics", {})
            strategies.append({
                "strategy_id": strategy_id,
                "metrics": {k: v.get("avg") for k, v in total.items()},
            })
    else:
        # Fallback for running/failed evaluations: check results then task
        results = source.get("results", [])
        if results:
            for r in results:
                strategies.append({
                    "strategy_id": r.get("strategy_id"),
                    "metrics": None,  # Not yet available
                })
        else:
            # Fall back to task definition
            strategy_ids = source.get("strategy_id", [])
            for strategy_id in strategy_ids:
                strategies.append({
                    "strategy_id": strategy_id,
                    "metrics": None,
                })

    return {
        "_id": _id,
        "workspace_id": source.get("workspace_id"),
        "benchmark_id": source.get("benchmark_id"),
        "strategies": strategies,
    }


# Judgements

def judgements_count_by_scenario(workspace_id: str) -> Dict[str, Any]:
    """
    Count judgements per scenario in a workspace.
    Returns {total, scenarios: [{scenario_id, count}, ...]} sorted by count descending.
    """
    body = {
        "size": 0,
        "query": {"term": {"workspace_id": workspace_id}},
        "aggs": {
            "by_scenario": {
                "terms": {"field": "scenario_id", "size": 10000}
            }
        },
    }
    es_response = es("studio").search(index="esrs-judgements", body=body)
    buckets = es_response.body.get("aggregations", {}).get("by_scenario", {}).get("buckets", [])
    scenarios = [{"scenario_id": b["key"], "count": b["doc_count"]} for b in buckets]
    return {
        "workspace_id": workspace_id,
        "total": sum(s["count"] for s in scenarios),
        "scenarios": scenarios,
    }
