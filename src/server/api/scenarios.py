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
from ..models import ScenarioCreate, ScenarioUpdate

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch

INDEX_NAME = "esrs-scenarios"

def search(
        workspace_id: str,
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """Search for scenarios.

    Args:
        workspace_id: The UUID of the workspace.
        text: Search text for filtering scenarios.
        filters: List of additional Elasticsearch filters.
        sort: Sorting configuration for the search.
        size: Number of scenarios to return per page.
        page: Page number for pagination.
        aggs: Whether to include aggregations (e.g., judgement counts).

    Returns:
        A dictionary containing the search results.
    """
    response = utils.search_assets(
        "scenarios", workspace_id, text, filters, sort, size, page,
        counts=[ "judgements" ] if aggs else [],
    )
    return response

def tags(workspace_id: str) -> Dict[str, Any]:
    """List all scenario tags (up to 10,000).

    Args:
        workspace_id: The UUID of the workspace.

    Returns:
        The response from Elasticsearch containing tag aggregations.
    """
    es_response = utils.search_tags("scenarios", workspace_id)
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """Get a scenario by its _id.

    Args:
        _id: The UUID of the scenario.

    Returns:
        The scenario document from Elasticsearch.
    """
    client = es("studio")
    es_response = client.get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(docs: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """
    Create one or more scenarios. Generates a deterministic _id per item for
    UX efficiency, and to prevent the creation of duplicate scenarios for the
    same values — scenarios never accept a caller-supplied `_id`.

    Accepts a list of scenario data. Each item is validated independently,
    so a validation failure on one item does not prevent the others from
    being created. Returns a single Elasticsearch `_bulk` response (one
    `refresh=True` for the whole batch, not one per item) with per-item
    results reported in `items`, in the same order as submitted.

    Args:
        docs: A list of scenario data to create.
        user: The username of the creator.

    Returns:
        The response from the Elasticsearch bulk index operation.
    """
    utils.assert_batch_size(docs)

    operations = []
    synthetic_items = {}
    for i, doc in enumerate(docs):
        try:
            # Create, validate, and dump model
            doc = ScenarioCreate.model_validate(doc, context={"user": user, "via": via}).serialize()
        except ValidationError as e:
            synthetic_items[i] = utils.bulk_error_item("index", INDEX_NAME, None, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc = utils.copy_fields_to_search("scenarios", doc)

        _id = utils.unique_id([ doc["workspace_id"], doc["values"] ])
        operations.append({ "index": { "_index": INDEX_NAME, "_id": _id }})
        operations.append(doc)

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(docs))

def update(docs: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """Update one or more scenarios.

    Accepts a list of partial scenario data; each item must carry its own
    `_id`. Each item is validated independently, so a validation failure on
    one item does not prevent the others from being updated. Returns a
    single Elasticsearch `_bulk` response (one `refresh=True` for the whole
    batch, not one per item) with per-item results reported in `items`, in
    the same order as submitted.

    Args:
        docs: A list of partial scenario data to update, each including `_id`.
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
            doc_partial = ScenarioUpdate.model_validate(doc_partial, context={"user": user, "via": via}).serialize()
        except ValidationError as e:
            synthetic_items[i] = utils.bulk_error_item("update", INDEX_NAME, _id, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc_partial = utils.copy_fields_to_search("scenarios", doc_partial)

        operations.append({ "update": { "_index": INDEX_NAME, "_id": _id }})
        operations.append({ "doc": doc_partial })

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(docs))

def delete(ids: List[str]) -> Dict[str, Any]:
    """Delete one or more scenarios and their associated judgements.

    Unlike the other bulk delete operations, this does not use Elasticsearch's
    `_bulk` API — it widens the existing `delete_by_query` cascade to match
    any of the given ids via a `terms` clause, so it always returns a single
    `delete_by_query` response regardless of how many ids are given, not a
    per-item bulk-shaped response.

    Args:
        ids: A list of scenario UUIDs to delete.

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
                                { "term": { "_index": "esrs-scenarios" }},
                                { "terms": { "_id": ids }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-judgements" }},
                                { "terms": { "scenario_id": ids }}
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
        index="esrs-scenarios,esrs-judgements",
        body=body,
        refresh=True,
        conflicts="proceed",
    )
    return es_response