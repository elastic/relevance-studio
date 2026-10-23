# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# Third-party packages
from pydantic import ValidationError

# App packages
from .. import utils
from ..client import es
from ..models import WorkspaceCreate, WorkspaceUpdate

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch

INDEX_NAME = "esrs-workspaces"

def search(
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """Search for workspaces.

    Args:
        text: Search text for filtering workspaces.
        filters: List of additional Elasticsearch filters.
        sort: Sorting configuration for the search.
        size: Number of workspaces to return per page.
        page: Page number for pagination.
        aggs: Whether to include aggregations (e.g., asset counts).

    Returns:
        A dictionary containing the search results.
    """
    response = utils.search_assets(
        "workspaces", None, text, filters, sort, size, page,
        counts=[ "displays", "scenarios", "judgements", "strategies", "benchmarks" ] if aggs else [],
    )
    return response

def tags() -> Dict[str, Any]:
    """List all workspace tags (up to 10,000).

    Returns:
        The response from Elasticsearch containing tag aggregations.
    """
    es_response = utils.search_tags("workspaces")
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """Get a workspace by its _id.

    Args:
        _id: The UUID of the workspace.

    Returns:
        The workspace document from Elasticsearch.
    """
    client = es("studio")
    es_response = client.get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(docs: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """Create one or more workspaces.

    Accepts a list of workspace data; each item may include an optional
    `_id` for idempotence. Each item is validated independently, so a
    validation failure on one item does not prevent the others from being
    created. Returns a single Elasticsearch `_bulk` response (one
    `refresh=True` for the whole batch, not one per item) with per-item
    results reported in `items`, in the same order as submitted.

    Args:
        docs: A list of workspace data to create.
        user: The username of the creator.

    Returns:
        The response from the Elasticsearch bulk index operation.
    """
    utils.assert_batch_size(docs)

    operations = []
    synthetic_items = {}
    for i, doc in enumerate(docs):
        doc = dict(doc)
        _id = doc.pop("_id", None) or utils.unique_id()
        try:
            # Create, validate, and dump model
            doc = WorkspaceCreate.model_validate(doc, context={"user": user, "via": via}).serialize()
        except ValidationError as e:
            synthetic_items[i] = utils.bulk_error_item("index", INDEX_NAME, _id, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc = utils.copy_fields_to_search("workspaces", doc)

        operations.append({ "index": { "_index": INDEX_NAME, "_id": _id }})
        operations.append(doc)

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(docs))

def update(docs: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """Update one or more workspaces.

    Accepts a list of partial workspace data; each item must carry its own
    `_id`. Each item is validated independently, so a validation failure on
    one item does not prevent the others from being updated. Returns a
    single Elasticsearch `_bulk` response (one `refresh=True` for the whole
    batch, not one per item) with per-item results reported in `items`, in
    the same order as submitted.

    Args:
        docs: A list of partial workspace data to update, each including `_id`.
        user: The username of the updater.

    Returns:
        The response from the Elasticsearch bulk update operation.
    """
    utils.assert_batch_size(docs)

    operations = []
    synthetic_items = {}
    for i, doc_partial in enumerate(docs):
        doc_partial = dict(doc_partial)
        _id = doc_partial.pop("_id", None)
        try:
            # Create, validate, and dump model
            doc_partial = WorkspaceUpdate.model_validate(doc_partial, context={"user": user, "via": via}).serialize()
        except ValidationError as e:
            synthetic_items[i] = utils.bulk_error_item("update", INDEX_NAME, _id, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc_partial = utils.copy_fields_to_search("workspaces", doc_partial)

        operations.append({ "update": { "_index": INDEX_NAME, "_id": _id }})
        operations.append({ "doc": doc_partial })

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(docs))

def delete(ids: List[str]) -> Dict[str, Any]:
    """Delete one or more workspaces and their associated assets.

    This deletes the workspaces and all displays, scenarios, judgements,
    strategies, benchmarks, and evaluations linked to them.

    Unlike the other bulk delete operations, this does not use Elasticsearch's
    `_bulk` API — it widens the existing `delete_by_query` cascade to match
    any of the given ids via a `terms` clause, so it always returns a single
    `delete_by_query` response regardless of how many ids are given, not a
    per-item bulk-shaped response.

    Args:
        ids: A list of workspace UUIDs to delete.

    Returns:
        The response from the Elasticsearch delete_by_query operation.
    """
    utils.assert_batch_size(ids)
    body = {
        "query": {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-workspaces" }},
                                { "terms": { "_id": ids }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-displays" }},
                                { "terms": { "workspace_id": ids }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-scenarios" }},
                                { "terms": { "workspace_id": ids }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-judgements" }},
                                { "terms": { "workspace_id": ids }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-strategies" }},
                                { "terms": { "workspace_id": ids }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-benchmark-configs" }},
                                { "terms": { "workspace_id": ids }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-benchmark-runs" }},
                                { "terms": { "workspace_id": ids }}
                            ]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
    client = es("studio")
    es_response = client.delete_by_query(
        index=",".join([
            "esrs-workspaces",
            "esrs-displays",
            "esrs-scenarios",
            "esrs-judgements",
            "esrs-strategies",
            "esrs-benchmark-configs",
            "esrs-benchmark-runs",
        ]),
        body=body,
        refresh=True,
        conflicts="proceed",
    )

    # Benchmark results + forensics collections are data streams that carry
    # workspace_id on every document, so each is swept directly by workspace_id
    # in a single query (no _index filter — data-stream docs live in rolling
    # backing indices). Tolerant of streams that don't exist yet.
    stream_body = { "query": { "terms": { "workspace_id": ids }}}
    for stream in (
        "esrs-benchmark-results",
        "esrs-benchmark-runtime-indices",
        "esrs-benchmark-runtime-strategies",
        "esrs-benchmark-runtime-scenarios",
        "esrs-benchmark-runtime-judgements",
        "esrs-benchmark-unrated-docs",
        "esrs-benchmark-failures",
    ):
        try:
            client.delete_by_query(
                index=stream, body=stream_body, refresh=True, conflicts="proceed",
            )
        except Exception:
            pass

    return es_response