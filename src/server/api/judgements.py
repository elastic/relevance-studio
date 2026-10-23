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
from ..models import JudgementCreate

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch

INDEX_NAME = "esrs-judgements"
SEARCH_FIELDS = utils.get_search_fields_from_mapping("judgements")

def search(
        workspace_id: str,
        scenario_id: str,
        index_pattern: str,
        query: Dict[str, Any] = {},
        query_string: str = "*",
        filter: str = None,
        sort: str = None,
        _source: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
    """Get documents from the content deployment with ratings joined to them.

    Args:
        workspace_id: The UUID of the workspace.
        scenario_id: The UUID of the scenario to retrieve judgements for.
        index_pattern: Elasticsearch index pattern to search against.
        query: A full Elasticsearch query DSL object. If provided, overrides `query_string`.
        query_string: A Lucene query string (defaults to "*").
        filter: Filtering criteria for rated vs unrated documents.
            Options: "rated", "rated-ai", "rated-human", "unrated".
        sort: Sorting criteria for the results.
            Options: "match" (BM25 score), "rating-newest", "rating-oldest".
        _source: Source filtering configuration with 'includes' and 'excludes'. Searches should set "_source.includes" as the value of "fields" from a display.

    Returns:
        A dictionary containing "hits" from Elasticsearch, where each hit has 
        the rating and metadata joined to the original document.
    """
    response = {}
        
    # Get judgements for scenario
    judgements = {}
    body = {
        "size": 10000,
        "query": {
            "bool": {
                "filter": [
                    { "term": { "workspace_id": workspace_id }},
                    { "term": { "scenario_id": scenario_id }}
                ]
            }
        },
        "_source": {
            "excludes": [
                "_search"
            ]
        }
    }
    if filter == "rated-human":
        body["query"]["bool"]["must_not"] = [
            {"term": {"@meta.updated_via": "mcp"}},
            {"term": {"@meta.updated_by": "ai"}},
        ]
    elif filter == "rated-ai":
        body["query"]["bool"]["filter"].append({
            "bool": {
                "should": [
                    {"term": {"@meta.updated_via": "mcp"}},
                    {"term": {"@meta.updated_by": "ai"}},
                ],
                "minimum_should_match": 1,
            }
        })
    if sort == "rating-newest":
        body["sort"] = [{
            "@meta.updated_at": "desc"
        }]
    elif sort == "rating-oldest":
        body["sort"] = [{
            "@meta.updated_at": "asc"
        }]
    s_client = es("studio")
    es_response = s_client.search(index="esrs-judgements", body=body)
    for hit in es_response.body.get("hits", {}).get("hits") or []:
        _index = hit["_source"]["index"]
        _id = hit["_source"]["doc_id"]
        if _index not in judgements:
            judgements[_index] = {}
        judgements[_index][_id] = {
            "_id": hit["_id"],
            "@meta": hit["_source"].get("@meta"),
            "rating": hit["_source"].get("rating"),
        }
        
    # Search docs on the content deployment
    # Exclude fields that exist only for searchability
    body = {
        "size": 48
    }
    if _source:
        body["_source"] = {}
        if _source.get("includes"):
            body["_source"]["includes"] = _source["includes"]
        if _source.get("excludes"):
            body["_source"]["excludes"] = _source["excludes"]
    if query:
        # From strategy editor UI
        body.update(query)
    else:
        # From judgements search UI
        body["query"] = {
            "bool": {
                "must": {
                    "query_string": {
                        "query": query_string or "*",
                        "default_operator": "AND"
                    }
                }
            }
        }
    
    # Filter docs by judgements (used judgement search UI)
    if filter and filter != "all":
        filter_clauses = []
        for _index in judgements.keys():
            filter_clauses.append({
                "bool": {
                    "filter": [
                        { "term": { "_index": _index }},
                        { "ids": { "values": list(judgements[_index].keys()) }}
                    ]
                }
            })
        if filter == "unrated":
            body["query"]["bool"]["must_not"] = filter_clauses
        else:
            body["query"]["bool"]["should"] = filter_clauses
            body["query"]["bool"]["minimum_should_match"] = 1
    if sort == "match":
        body["sort"] = [{
            "_score": "desc"
        }]
    c_client = es("content")
    es_response = c_client.search(index=index_pattern, body=body)
    
    # Merge docs and ratings
    response["hits"] = es_response.body["hits"]
    for i, hit in enumerate(response["hits"]["hits"]):
        response["hits"]["hits"][i] = {
            "_id": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("_id"),
            "@meta": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("@meta"),
            "rating": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("rating"),
            "doc": hit
        }
    if response["hits"]["hits"] and sort in ( "rating-newest", "rating-oldest" ):
        reverse = True if sort == "rating-newest" else False
        fallback = "0000-01-01T00:00:00Z" if not reverse else "9999-12-31T23:59:59Z"
        response["hits"]["hits"] = sorted(response["hits"]["hits"], key=lambda hit: (hit.get("@meta") or {}).get("created_at") or fallback, reverse=reverse)
    return response

PAINLESS_SCRIPTED_UPSERT_SOURCE = """
    if (ctx.op == 'create') {
        ctx._source.rating = params.rating;
        ctx._source['@meta'] = [
            'created_at': params.now,
            'created_by': params.username,
            'created_via': params.via,
            'updated_at': params.now,
            'updated_by': params.username,
            'updated_via': params.via
        ];
    } else {
        ctx._source.rating = params.rating;
        ctx._source['@meta'].updated_at = params.now;
        ctx._source['@meta'].updated_by = params.username;
        ctx._source['@meta'].updated_via = params.via;
    }
"""

def set(workspace_id: str, judgements: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """Create or update one or more judgements in a single workspace.

    Generates a deterministic _id per item (from workspace_id, scenario_id,
    index, and doc_id) for UX efficiency, and to prevent the creation of
    duplicate judgements for the same combination of scenario, index, and
    doc — including duplicates submitted within the same batch: a repeated
    {scenario_id, index, doc_id} in one call resolves to the same _id and is
    applied as a second scripted-upsert update against the same document
    within the same `_bulk` call, not as two separate documents.

    Accepts a list of `{scenario_id, index, doc_id, rating}` items; `_id` is
    always derived and is never accepted as input. Each item is validated
    independently, so a validation failure on one item does not prevent the
    others from being set. Returns a single Elasticsearch `_bulk` response
    (one `refresh=True` for the whole batch, not one per item) with per-item
    results reported in `items`, in the same order as submitted.

    Args:
        workspace_id: The UUID of the workspace.
        judgements: A list of `{scenario_id, index, doc_id, rating}` items.
        user: The username of the user performing the operation.

    Returns:
        The response from the Elasticsearch bulk update operation.
    """
    utils.assert_batch_size(judgements)

    operations = []
    synthetic_items = {}
    context = {"user": user, "via": via}
    for i, j in enumerate(judgements):
        try:
            # Create, validate, and dump model
            doc = JudgementCreate.model_validate(
                {
                    "workspace_id": workspace_id,
                    "scenario_id": j["scenario_id"],
                    "index": j["index"],
                    "doc_id": j["doc_id"],
                    "rating": j["rating"],
                },
                context=context,
            ).serialize()
        except (ValidationError, KeyError) as e:
            synthetic_items[i] = utils.bulk_error_item("update", INDEX_NAME, None, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc = utils.copy_fields_to_search("judgements", doc)

        _id = utils.unique_id([
            doc["workspace_id"],
            doc["scenario_id"],
            doc["index"],
            doc["doc_id"],
        ])
        operations.append({ "update": { "_index": INDEX_NAME, "_id": _id }})
        operations.append({
            "scripted_upsert": True,
            "script": {
                "source": PAINLESS_SCRIPTED_UPSERT_SOURCE,
                "lang": "painless",
                "params": {
                    "rating": doc["rating"],
                    "now": doc["@meta"]["created_at"],
                    "username": doc["@meta"]["created_by"],
                    "via": doc["@meta"].get("created_via") or doc["@meta"].get("updated_via") or "api"
                }
            },
            "upsert": doc
        })

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(judgements))

def unset(ids: List[str]) -> Dict[str, Any]:
    """Delete one or more judgements by their _ids.

    Args:
        ids: A list of judgement UUIDs to delete.

    Returns:
        The response from the Elasticsearch bulk delete operation.
    """
    utils.assert_batch_size(ids)
    operations = [{ "delete": { "_index": INDEX_NAME, "_id": _id }} for _id in ids]
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, {}, len(ids))