# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
FastMCP server with MCP Resources for selective data access.

This is an alternative to fastmcp.py that adds MCP Resources alongside tools.
Resources provide filtered/projected views of data, dramatically reducing
response sizes (e.g., 100KB -> 2KB for evaluation summaries).

Run on port 4201 to avoid conflict with the standard server on 4200.
"""

# Standard packages
import base64
import os
from io import BytesIO
from typing import Any, Dict, List, Optional

# Third-party packages
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from PIL import Image
from starlette.requests import Request
from starlette.responses import JSONResponse

# App packages
from . import api
from .client import es
from .models import *

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()


####  Helpers  #################################################################

def _int(value, default=None):
    """Coerce value to int, handling strings from MCP clients."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _bool(value, default=False):
    """Coerce value to bool, handling strings from MCP clients."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)

####  Application  #############################################################

instructions = """
Elasticsearch Relevance Studio is an application that manages the lifecycle of
search relevance engineering in Elasticsearch. Generally, its goal is to help
people deliver amazing search experiences by guiding them in the best practices
of search relevance engineering. That means defining scenarios, curating
judgements, building strategies, and benchmarking their performance.

## Application architecture

- **Studio deployment** - An Elasticsearch deployment that stores the assets created by the **server**.
- **Content deployment** - A Elasticsearch deployment that stores the documents that will be searched, judged, and used in rank evaluation.
- **Server** - A Flask server that handles API requests and interfaces with the **studio deployment** and **content deployment**.
- **MCP server** - A FastMCP server that handles MCP requests and interfaces with the **studio deployment** and **content deployment**.
- **Worker** - A background process that polls for pending evaluations in the **studio deployment**, runs them, and saves their results in the **studio deployment**.
- **UI** - A React application for the UX that interfaces with the **server**.

## Studio deployment data assets

- **workspaces** - A namespace for all assets whose workspace_id matches the workspace _id.
- **displays** - A markdown template to render documents from specific indices in the **UI**.
- **scenarios** - A search input (e.g. "brown oxfords")
- **judgements** - A rating for a given document from a given index for a given scenario.
- **strategies** - An Elasticsearch search template whose params are supplied by scenario values.
- **benchmarks** - A reusable task definition for evaluations.
- **evaluations** - The results of a gridded rank evaluation.

## General workflow

Here is the typical workflow of the application:

1. Select a workspace to work in.
    - Take note of "_id", "name", "index_pattern", "rating_scale", and "params".
2. Use displays to control the retrieval and display of documents from indices in the content deployment.
    - "index_pattern" is the Elasticsearch index pattern that the display. When multiple displays have overlapping "index_pattern" values, the more specific matching pattern should be used.
    - "fields" lists the fields that should be in the _source.includes of all searches to that index pattern.
    - "template.image.url" is an image for the document. It might contain mustache variables, which should be replaced by their respective values from "fields".
3. Define a diverse set of scenarios that are representative of the use case.
4. Curate judgements for each scenario using the workspace rating scale.
    - "rating_scale_max" represents superb relevance.
    - "rating_scale.min" represents complete irrelevance.
    - "index" in judgements is the index of the doc being rated.
    - "doc_id" in judgements is the _id of the doc being rated.
5. Build strategies that attempt to maximize search relevance.
    - Strategies are the bodies of Elasticsearch Search API, which is a "query" or "retriever".
    - Strategies must implement at least one of the params from the workspace in the form of a Mustache variables. Example: "{{ text }}"
6. Define benchmarks.
7. Run evaluations for a benchmark.
    - A worker process will execute these asynchronously. It may take seconds or minutes to complete.
8. Analyze the results of the evaluations.
    - The "summary" field summarizes the relevance metrics for each strategy_id or strategy_tag.
9. Find ways to enhance the process, such as:
    - Creating scenarios that would be valuable to include in benchmarks;
    - Adjusting the tags of scenarios or strategies;
    - Setting the ratings of documents that should be judged;
    - Changing or unsetting the ratings of judgements that might be inaccurate;
    - Enhancing the query logic of strategies; and
    - Re-running evaluations, analyzing their results, and repeating the workflow.

## Instructions

You are an expert in Elasticsearch and search relevance engineering.

You automate the management of resources and evaluations in Relevance Studio.

You must adhere to the following requirements and best practices:

## Requirements

### 1. Always scope operations on studio assets by workspace_id

All operations on **studio deployment data assets** must be scoped to a workspace.
If I ask you to perform a search, create, update, set, unset, or delete on
displays, scenarios, judgements, strategies, benchmarks or evaluations, pass the
workspace_id that you're currently working on as an argument to that function.

If you aren't working on a workspace or you forgot which one it was, ask me for
clarification on which workspace you should be using. If I give you an _id
(which is a UUID), then use that as the workspace_id. If I give you a name or a
description instead, then search for the workspace that best matches it and use
that _id. If there are no good matches, let me know, and don't perform the
operation.

### 2. Always fetch displays before searching or judging documents from the content deployment

Fetch all displays for the workspace before searching or judging documents from
the content deployment. Use the display whose index_pattern best matches the
index of the documents that you will be searching or judging. If there is a
matching display, use the values of its "fields" as the values of
_source.includes in your searches. This will make searching much more efficient.
If thers is no matching display, then don't set the value of _source.includes
in your searches.

In other words, always ensure you have tried fetching displays with the
displays_search tool before using either the content_search tool or the
judgements_search tool.

## Best Practices

### Prefer MCP Resources over Tools for reading data

This server exposes **MCP Resources** in addition to tools. Resources provide
selective access to large objects, dramatically reducing response sizes.

**Evaluation resources** (use instead of evaluations_get which returns 100KB+):
- `evaluations://{id}/status` - Check if complete (status, took, error)
- `evaluations://{id}/summary` - Aggregated metrics by strategy
- `evaluations://{id}/task` - What was configured
- `evaluations://{id}/results/{strategy_id}` - Detailed results for one strategy
- `evaluations://{id}/unrated` - Documents needing judgements

**Listing resources** (lightweight overviews):
- `workspaces://list` - All workspaces (_id, name, index_pattern, params)
- `strategies://{workspace_id}/list` - All strategies (_id, name, tags)
- `scenarios://{workspace_id}/list` - All scenarios (_id, name, values, tags)
- `benchmarks://{workspace_id}/list` - All benchmarks (_id, name, description, tags)

**Preferred workflow for evaluations:**
1. After running an evaluation, read `evaluations://{id}/status` to check completion
2. Once complete, read `evaluations://{id}/summary` for metrics
3. Only fetch detailed results with `evaluations://{id}/results/{strategy_id}` if needed

### Analyze images when judging documents

When judging documents that have a display template, check to see if the
display defines an image URL template, which you can reconstruct by replacing
mustache variables with fields from the document. You can use the
get_base64_image_from_url tool to fetch that image in a small, base64-encoded
format. This can be a great signal for relevance.

### Other requirements

Don't make up fictional values for any "_id" or "doc_id" field of any asset.
Look them up if needed.
"""

mcp = FastMCP(name="Relevance Studio (Resources)", instructions=instructions)


################################################################################
#                                                                              #
#                              MCP RESOURCES                                   #
#                                                                              #
#  Resources provide selective, filtered access to data. Use these instead     #
#  of tools when you only need specific parts of large objects.                #
#                                                                              #
################################################################################


####  Resources: Workspaces  ###################################################

def _get_workspaces_list() -> dict:
    """Internal helper for workspaces list."""
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
    return {"count": len(workspaces), "workspaces": workspaces}


@mcp.resource("workspaces://list")
def workspaces_list_all() -> dict:
    """Get a lightweight list of all workspaces."""
    return _get_workspaces_list()


####  Resources: Displays  #####################################################

@mcp.resource("displays://{workspace_id}/list")
def displays_list(workspace_id: str) -> dict:
    """
    Get a lightweight list of all displays in a workspace.
    Returns _id, index_pattern, and field names.
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
    return {
        "workspace_id": workspace_id,
        "count": len(displays),
        "displays": displays,
    }


####  Resources: Scenarios  ####################################################

def _get_scenarios_list(workspace_id: str = "") -> dict:
    """Internal helper for scenarios list."""
    es_response = api.scenarios.search(workspace_id=workspace_id, size=1000)
    hits = es_response.body.get("hits", {}).get("hits", [])
    scenarios = []
    for hit in hits:
        source = hit.get("_source", {})
        item = {
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "values": source.get("values", {}),
            "tags": source.get("tags", []),
        }
        if not workspace_id:
            item["workspace_id"] = source.get("workspace_id")
        scenarios.append(item)
    result = {"count": len(scenarios), "scenarios": scenarios}
    if workspace_id:
        result["workspace_id"] = workspace_id
    return result


@mcp.resource("scenarios://{workspace_id}/list")
def scenarios_list_by_workspace(workspace_id: str) -> dict:
    """Get a lightweight list of all scenarios in a workspace."""
    return _get_scenarios_list(workspace_id)


@mcp.resource("scenarios://{workspace_id}/by-tag/{tag}")
def scenarios_by_tag(workspace_id: str, tag: str) -> dict:
    """
    Get scenarios filtered by a specific tag.
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


####  Resources: Strategies  ###################################################

def _get_strategies_list(workspace_id: str = "") -> dict:
    """Internal helper for strategies list."""
    es_response = api.strategies.search(workspace_id=workspace_id, size=1000)
    hits = es_response.body.get("hits", {}).get("hits", [])
    strategies = []
    for hit in hits:
        source = hit.get("_source", {})
        item = {
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "tags": source.get("tags", []),
        }
        if not workspace_id:
            item["workspace_id"] = source.get("workspace_id")
        strategies.append(item)
    result = {"count": len(strategies), "strategies": strategies}
    if workspace_id:
        result["workspace_id"] = workspace_id
    return result


@mcp.resource("strategies://{workspace_id}/list")
def strategies_list_by_workspace(workspace_id: str) -> dict:
    """Get a lightweight list of all strategies in a workspace."""
    return _get_strategies_list(workspace_id)


@mcp.resource("strategies://{workspace_id}/by-tag/{tag}")
def strategies_by_tag(workspace_id: str, tag: str) -> dict:
    """
    Get strategies filtered by a specific tag.
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


@mcp.resource("strategies://{_id}/template")
def strategy_template(_id: str) -> dict:
    """
    Get just the template source for a specific strategy.
    """
    es_response = api.strategies.get(_id)
    source = es_response.body.get("_source", {})
    template = source.get("template", {})
    return {
        "_id": _id,
        "name": source.get("name"),
        "template": template,
    }


####  Resources: Benchmarks  ###################################################

def _get_benchmarks_list(workspace_id: str = "") -> dict:
    """Internal helper for benchmarks list."""
    es_response = api.benchmarks.search(workspace_id=workspace_id, size=1000)
    hits = es_response.body.get("hits", {}).get("hits", [])
    benchmarks = []
    for hit in hits:
        source = hit.get("_source", {})
        item = {
            "_id": hit.get("_id"),
            "name": source.get("name"),
            "description": source.get("description"),
            "tags": source.get("tags", []),
        }
        if not workspace_id:
            item["workspace_id"] = source.get("workspace_id")
        benchmarks.append(item)
    result = {"count": len(benchmarks), "benchmarks": benchmarks}
    if workspace_id:
        result["workspace_id"] = workspace_id
    return result


@mcp.resource("benchmarks://{workspace_id}/list")
def benchmarks_list_by_workspace(workspace_id: str) -> dict:
    """Get a lightweight list of all benchmarks in a workspace."""
    return _get_benchmarks_list(workspace_id)


@mcp.resource("benchmarks://{_id}/task")
def benchmark_task(_id: str) -> dict:
    """
    Get the task definition for a specific benchmark.
    """
    es_response = api.benchmarks.get(_id)
    source = es_response.body.get("_source", {})
    return {
        "_id": _id,
        "name": source.get("name"),
        "task": source.get("task", {}),
    }


####  Resources: Evaluations  ##################################################

def _get_evaluations_list(workspace_id: str) -> dict:
    """Internal helper for evaluations list.

    Note: Uses direct ES query because api.evaluations.search requires benchmark_id
    and always filters by it, making workspace-only queries impossible.
    """
    body = {
        "query": {"bool": {"filter": [{"term": {"workspace_id": workspace_id}}]}},
        "size": 1000,
        "_source": {"excludes": ["_search", "results", "summary"]},
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
    return {"count": len(evaluations), "evaluations": evaluations, "workspace_id": workspace_id}


@mcp.resource("evaluations://{workspace_id}/list")
def evaluations_list_by_workspace(workspace_id: str) -> dict:
    """Get a lightweight list of all evaluations in a workspace."""
    return _get_evaluations_list(workspace_id)


def _get_evaluation_status(_id: str) -> dict:
    """Internal helper for evaluation status."""
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    meta = source.get("@meta", {})
    return {
        "_id": _id,
        "status": meta.get("status"),
        "started_at": meta.get("started_at"),
        "started_by": meta.get("started_by"),
        "took": source.get("took"),
        "error": source.get("error"),
    }


def _get_evaluation_summary(_id: str) -> dict:
    """Internal helper for evaluation summary."""
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    return {
        "_id": _id,
        "status": source.get("@meta", {}).get("status"),
        "summary": source.get("summary", {}),
        "took": source.get("took"),
    }


def _get_evaluation_results_by_strategy(_id: str, strategy_id: str) -> dict:
    """Internal helper for evaluation results by strategy."""
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
            "strategy_id": strategy_id,
            "error": f"Strategy {strategy_id} not found in evaluation results",
            "available_strategies": [r.get("strategy_id") for r in results]
        }

    return {
        "_id": _id,
        "strategy_id": strategy_id,
        "searches": strategy_results.get("searches", []),
        "failures": strategy_results.get("failures", []),
    }


@mcp.resource("evaluations://{_id}/status")
def evaluation_status_resource(_id: str) -> dict:
    """Get just the status and metadata of an evaluation."""
    return _get_evaluation_status(_id)


@mcp.resource("evaluations://{_id}/summary")
def evaluation_summary_resource(_id: str) -> dict:
    """Get just the summary metrics of a completed evaluation."""
    return _get_evaluation_summary(_id)


@mcp.resource("evaluations://{_id}/task")
def evaluation_task(_id: str) -> dict:
    """Get the task definition of an evaluation."""
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


@mcp.resource("evaluations://{_id}/results/{strategy_id}")
def evaluation_results_by_strategy(_id: str, strategy_id: str) -> dict:
    """Get results for a specific strategy from an evaluation."""
    return _get_evaluation_results_by_strategy(_id, strategy_id)


@mcp.resource("evaluations://{_id}/unrated")
def evaluation_unrated_docs(_id: str) -> dict:
    """
    Get the list of unrated documents found during an evaluation.
    Useful for identifying which documents need judgements.
    """
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    return {
        "_id": _id,
        "unrated_docs": source.get("unrated_docs", []),
    }


@mcp.resource("evaluations://{_id}/strategies")
def evaluation_strategies(_id: str) -> dict:
    """
    Get list of strategy IDs that were evaluated, with their summary metrics.
    """
    es_response = api.evaluations.get(_id)
    source = es_response.body.get("_source", {})
    summary = source.get("summary", {})
    strategy_summaries = summary.get("strategy_id", {})

    strategies = []
    for strategy_id, metrics in strategy_summaries.items():
        total = metrics.get("_total", {}).get("metrics", {})
        strategies.append({
            "strategy_id": strategy_id,
            "metrics": {k: v.get("avg") for k, v in total.items()},
        })

    return {
        "_id": _id,
        "strategies": strategies,
    }


################################################################################
#                                                                              #
#                           LIGHTWEIGHT READ TOOLS                             #
#                                                                              #
#  These tools return filtered data like resources do, but work in all         #
#  MCP clients (including Cursor which doesn't support resources).             #
#                                                                              #
################################################################################


@mcp.tool()
def workspaces_list() -> Dict[str, Any]:
    """
    Get a lightweight list of all workspaces.
    Returns just _id, name, index_pattern, params, rating_scale, and tags.
    Faster than workspaces_search - use this for browsing.
    """
    return _get_workspaces_list()


@mcp.tool()
def scenarios_list(workspace_id: str) -> Dict[str, Any]:
    """
    Get a lightweight list of all scenarios in a workspace.
    Returns just _id, name, values, and tags.
    Faster than scenarios_search - use this for browsing.
    """
    return _get_scenarios_list(workspace_id)


@mcp.tool()
def strategies_list(workspace_id: str) -> Dict[str, Any]:
    """
    Get a lightweight list of all strategies in a workspace.
    Returns just _id, name, and tags - not the full template source.
    Faster than strategies_search - use this for browsing.
    """
    return _get_strategies_list(workspace_id)


@mcp.tool()
def benchmarks_list(workspace_id: str) -> Dict[str, Any]:
    """
    Get a lightweight list of all benchmarks in a workspace.
    Returns just _id, name, description, and tags.
    Faster than benchmarks_search - use this for browsing.
    """
    return _get_benchmarks_list(workspace_id)


@mcp.tool()
def evaluations_list(workspace_id: str) -> Dict[str, Any]:
    """
    Get a lightweight list of all evaluations in a workspace.
    Returns just _id, benchmark_id, status, started_at, and took.
    Faster than evaluations_search - use this for browsing.
    """
    return _get_evaluations_list(workspace_id)


@mcp.tool()
def evaluation_status(_id: str) -> Dict[str, Any]:
    """
    Get just the status and metadata of an evaluation.
    Use this to check if an evaluation is complete before fetching full results.
    Much smaller than evaluations_get.
    """
    return _get_evaluation_status(_id)


@mcp.tool()
def evaluation_summary(_id: str) -> Dict[str, Any]:
    """
    Get just the summary metrics of a completed evaluation.
    Contains aggregated metrics by strategy_id and strategy_tag.
    Much smaller than evaluations_get (2KB vs 100KB).
    """
    return _get_evaluation_summary(_id)


@mcp.tool()
def evaluation_results_for_strategy(_id: str, strategy_id: str) -> Dict[str, Any]:
    """
    Get results for a specific strategy from an evaluation.
    Returns searches (metrics + hits per scenario) for just that strategy.
    Much smaller than evaluations_get.
    """
    return _get_evaluation_results_by_strategy(_id, strategy_id)


@mcp.tool()
def latest_evaluation_summary(workspace_id: str) -> Dict[str, Any]:
    """
    Get the summary of the most recent completed evaluation in a workspace.
    Combines evaluations_list + evaluation_summary into a single call.
    Returns the evaluation _id, status, took, and summary metrics.
    If no completed evaluation exists, returns an error message.
    """
    # Get all evaluations sorted by started_at
    body = {
        "query": {"bool": {"filter": [{"term": {"workspace_id": workspace_id}}]}},
        "size": 100,
        "sort": [{"@meta.started_at": {"order": "desc"}}],
        "_source": ["@meta", "took", "benchmark_id", "summary"],
    }
    es_response = es("studio").search(index="esrs-evaluations", body=body)
    hits = es_response.body.get("hits", {}).get("hits", [])

    # Find the most recent completed evaluation
    for hit in hits:
        source = hit.get("_source", {})
        meta = source.get("@meta", {})
        if meta.get("status") == "completed":
            return {
                "_id": hit.get("_id"),
                "workspace_id": workspace_id,
                "benchmark_id": source.get("benchmark_id"),
                "status": "completed",
                "started_at": meta.get("started_at"),
                "took": source.get("took"),
                "summary": source.get("summary", {}),
            }

    # No completed evaluation found
    return {
        "workspace_id": workspace_id,
        "error": "No completed evaluation found in this workspace",
        "total_evaluations": len(hits),
    }


################################################################################
#                                                                              #
#                                MCP TOOLS                                     #
#                                                                              #
#  Tools for creating, updating, and deleting data. Use resources for reading. #
#                                                                              #
################################################################################


####  API: Workspaces  #########################################################

@mcp.tool(description=api.workspaces.search.__doc__)
def workspaces_search(
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Any = 10,
        page: Any = 1,
        aggs: Any = False,
    ) -> Dict[str, Any]:
    return dict(api.workspaces.search(text, filters, sort, _int(size, 10), _int(page, 1), _bool(aggs)))

@mcp.tool(description=api.workspaces.get.__doc__)
def workspaces_get(_id: str) -> Dict[str, Any]:
    return dict(api.workspaces.get(_id))

@mcp.tool(description=api.workspaces.create.__doc__ + f"""\n
JSON schema for doc:\n\n{WorkspaceCreate.model_input_json_schema()}
""")
def workspaces_create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    return dict(api.workspaces.create(doc, _id, user="ai"))

@mcp.tool(description=api.workspaces.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{WorkspaceUpdate.model_input_json_schema()}
""")
def workspaces_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.workspaces.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.workspaces.delete.__doc__)
def workspaces_delete(_id: str) -> Dict[str, Any]:
    return dict(api.workspaces.delete(_id))


####  API: Displays  ###########################################################

@mcp.tool(description=api.displays.search.__doc__)
def displays_search(
        workspace_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Any = 10,
        page: Any = 1,
        aggs: Any = False,
    ) -> Dict[str, Any]:
    return dict(api.displays.search(workspace_id, text, filters, sort, _int(size, 10), _int(page, 1), _bool(aggs)))

@mcp.tool(description=api.displays.get.__doc__)
def displays_get(_id: str) -> Dict[str, Any]:
    return dict(api.displays.get(_id))

@mcp.tool(description=api.displays.create.__doc__ + f"""\n
JSON schema for doc:\n\n{DisplayCreate.model_input_json_schema()}
""")
def displays_create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    return dict(api.displays.create(doc, _id, user="ai"))

@mcp.tool(description=api.displays.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{DisplayUpdate.model_input_json_schema()}
""")
def displays_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.displays.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.displays.delete.__doc__)
def displays_delete(_id: str) -> Dict[str, Any]:
    return dict(api.displays.delete(_id))


####  API: Scenarios  ##########################################################

@mcp.tool(description=api.scenarios.search.__doc__)
def scenarios_search(
        workspace_id: str,
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Any = 10,
        page: Any = 1,
        aggs: Any = False,
    ) -> Dict[str, Any]:
    return dict(api.scenarios.search(workspace_id, text, filters, sort, _int(size, 10), _int(page, 1), _bool(aggs)))

@mcp.tool(description=api.scenarios.tags.__doc__)
def scenarios_tags(workspace_id: str) -> Dict[str, Any]:
    return dict(api.scenarios.tags(workspace_id))

@mcp.tool(description=api.scenarios.get.__doc__)
def scenarios_get(_id: str) -> Dict[str, Any]:
    return dict(api.scenarios.get(_id))

@mcp.tool(description=api.scenarios.create.__doc__ + f"""\n
JSON schema for doc:\n\n{ScenarioCreate.model_input_json_schema()}
""")
def scenarios_create(doc: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.scenarios.create(doc, user="ai"))

@mcp.tool(description=api.scenarios.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{ScenarioUpdate.model_input_json_schema()}
""")
def scenarios_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.scenarios.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.scenarios.delete.__doc__)
def scenarios_delete(_id: str) -> Dict[str, Any]:
    return dict(api.scenarios.delete(_id))


####  API: Judgements  #########################################################

@mcp.tool(description=api.judgements.search.__doc__)
def judgements_search(
        workspace_id: str,
        scenario_id: str,
        index_pattern: str,
        query: Dict[str, Any] = {},
        query_string: str = "*",
        filter: str = None,
        sort: str = None,
        _source: Dict[str, Any] = None
    ) -> Dict[str, Any]:
    return dict(api.judgements.search(workspace_id, scenario_id, index_pattern, query, query_string, filter, sort, _source))

@mcp.tool(description=api.judgements.set.__doc__ + f"""\n
JSON schema for doc:\n\n{JudgementCreate.model_input_json_schema()}
""")
def judgements_set(doc: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.judgements.set(doc, user="ai"))

@mcp.tool(description=api.judgements.unset.__doc__)
def judgements_unset(_id: str) -> Dict[str, Any]:
    return dict(api.judgements.unset(_id))


####  API: Strategies  #########################################################

@mcp.tool(description=api.strategies.search.__doc__)
def strategies_search(
        workspace_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Any = 10,
        page: Any = 1,
        aggs: Any = False,
    ) -> Dict[str, Any]:
    return dict(api.strategies.search(workspace_id, text, filters, sort, _int(size, 10), _int(page, 1), _bool(aggs)))

@mcp.tool(description=api.strategies.tags.__doc__)
def strategies_tags(workspace_id: str) -> Dict[str, Any]:
    return dict(api.strategies.tags(workspace_id))

@mcp.tool(description=api.strategies.get.__doc__)
def strategies_get(_id: str) -> Dict[str, Any]:
    return dict(api.strategies.get(_id))

@mcp.tool(description=api.strategies.create.__doc__ + f"""\n
JSON schema for doc:\n\n{StrategyCreate.model_input_json_schema()}
""")
def strategies_create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    return dict(api.strategies.create(doc, _id, user="ai"))

@mcp.tool(description=api.strategies.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{StrategyUpdate.model_input_json_schema()}
""")
def strategies_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.strategies.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.strategies.delete.__doc__)
def strategies_delete(_id: str) -> Dict[str, Any]:
    return dict(api.strategies.delete(_id))


####  API: Benchmarks  #########################################################

@mcp.tool(description=api.benchmarks.search.__doc__)
def benchmarks_search(
        workspace_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Any = 10,
        page: Any = 1,
        aggs: Any = False,
    ) -> Dict[str, Any]:
    return dict(api.benchmarks.search(workspace_id, text, filters, sort, _int(size, 10), _int(page, 1), _bool(aggs)))

@mcp.tool(description=api.benchmarks.tags.__doc__)
def benchmarks_tags(workspace_id: str) -> Dict[str, Any]:
    return dict(api.benchmarks.tags(workspace_id))

@mcp.tool(description=api.benchmarks.make_candidate_pool.__doc__)
def benchmarks_make_candidate_pool(workspace_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.benchmarks.make_candidate_pool(workspace_id, task))

@mcp.tool(description=api.benchmarks.get.__doc__)
def benchmarks_get(_id: str) -> Dict[str, Any]:
    return dict(api.benchmarks.get(_id))

@mcp.tool(description=api.benchmarks.create.__doc__ + f"""\n
JSON schema for doc:\n\n{BenchmarkCreate.model_input_json_schema()}
""")
def benchmarks_create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    return dict(api.benchmarks.create(doc, _id, user="ai"))

@mcp.tool(description=api.benchmarks.update.__doc__ + f"""\n
JSON schema for doc:\n\n{BenchmarkUpdate.model_input_json_schema()}
""")
def benchmarks_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.benchmarks.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.benchmarks.delete.__doc__)
def benchmarks_delete(_id: str) -> Dict[str, Any]:
    return dict(api.benchmarks.delete(_id))


####  API: Evaluations  ########################################################

@mcp.tool(description=api.evaluations.search.__doc__)
def evaluations_search(
        workspace_id: str = "",
        benchmark_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Any = 10,
        page: Any = 1,
        aggs: Any = False,
    ) -> Dict[str, Any]:
    return dict(api.evaluations.search(workspace_id, benchmark_id, text, filters, sort, _int(size, 10), _int(page, 1), _bool(aggs)))

@mcp.tool(description=api.evaluations.get.__doc__)
def evaluations_get(_id: str) -> Dict[str, Any]:
    return dict(api.evaluations.get(_id))

@mcp.tool(description=api.evaluations.create.__doc__ + f"""\n
JSON schema for doc:\n\n{EvaluationCreate.model_input_json_schema()}
""")
def evaluations_create(workspace_id: str, benchmark_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.evaluations.create(workspace_id, benchmark_id, task, user="ai"))

@mcp.tool(description=api.evaluations.run.__doc__)
def evaluations_run(evaluation: Dict[str, Any], store_results: Optional[bool] = False) -> Dict[str, Any]:
    return dict(api.evaluations.run(evaluation, _bool(store_results)))

@mcp.tool(description=api.evaluations.delete.__doc__)
def evaluations_delete(_id: str) -> Dict[str, Any]:
    return dict(api.evaluations.delete(_id))


####  API: Content  ############################################################

@mcp.tool(description=api.content.search.__doc__)
def content_search(index_patterns: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.content.search(index_patterns, body))

@mcp.tool(description=api.content.mappings_browse.__doc__)
def content_mappings_browse(index_patterns: str) -> Dict[str, Any]:
    return dict(api.content.mappings_browse(index_patterns))


####  API: Setup  ##############################################################

@mcp.tool(description=api.setup.check.__doc__)
def setup_check() -> Dict[str, Any]:
    return api.setup.check()

@mcp.tool(description=api.setup.run.__doc__)
def setup_run() -> Dict[str, Any]:
    return api.setup.run()


####  Utils  ###################################################################

@mcp.tool(description="Get the base64 encoding of an image URL.")
def get_base64_image_from_url(url: str, max_size: int = 50) -> str:
    response = requests.get(url)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        raise ValueError(f"URL does not point to an image. Content-Type: {content_type}")

    # Resize image
    image = Image.open(BytesIO(response.content))
    image.thumbnail((max_size, max_size), Image.LANCZOS)
    buffer = BytesIO()
    format = image.format or content_type.split("/")[1].upper()
    if format == "JPG":
        format = "JPEG" # pillow expects "JPEG"
    image.save(buffer, format=format)
    buffer.seek(0)

    # Encode as base64
    encoded = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:{content_type};base64,{encoded}"


####  Health checks  ###########################################################

@mcp.tool
def healthz_mcp() -> Dict[str, Any]:
    """
    Test if application is running.
    """
    return { "acknowledged": True }

@mcp.custom_route("/healthz", methods=["GET"])
def healthz_http(request: Request) -> JSONResponse:
    """
    Test if application is running.
    """
    return JSONResponse({ "acknowledged": True })


####  Main  ####################################################################

if __name__ == "__main__":
    mcp.run(transport="http", port=4201, log_level="debug")
