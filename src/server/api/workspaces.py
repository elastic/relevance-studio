# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict, List, Optional, TYPE_CHECKING

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
        es_client: Optional["Elasticsearch"] = None,
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
        es_client=es_client,
    )
    return response

def tags(es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
    """List all workspace tags (up to 10,000).

    Returns:
        The response from Elasticsearch containing tag aggregations.
    """
    es_response = utils.search_tags("workspaces", es_client=es_client)
    return es_response

def get(_id: str, source_includes: Optional[List[str]] = None, es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
    """Get a workspace by its _id.

    Args:
        _id: The UUID of the workspace.
        source_includes: Optional list of source fields to return (e.g. ["name", "params"]).

    Returns:
        The workspace document from Elasticsearch.
    """
    client = es_client if es_client is not None else es("studio")
    kwargs = dict(index=INDEX_NAME, id=_id, source_excludes="_search")
    if source_includes is not None:
        kwargs["source_includes"] = source_includes
    es_response = client.get(**kwargs)
    return es_response

def create(doc: Dict[str, Any], _id: str = None, user: str = None, via: str = None, es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
    """Create a workspace.

    Args:
        doc: The workspace data to create.
        _id: Optional pregenerated UUID for idempotence.
        user: The username of the creator.

    Returns:
        The response from the Elasticsearch index operation.
    """
    
    # Create, validate, and dump model
    doc = WorkspaceCreate.model_validate(doc, context={"user": user, "via": via}).serialize()

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("workspaces", doc)
    
    # Submit
    client = es_client if es_client is not None else es("studio")
    es_response = client.index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any], user: str = None, via: str = None, es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
    """Update a workspace by its _id.

    Args:
        _id: The UUID of the workspace.
        doc_partial: The partial workspace data to update.
        user: The username of the updater.

    Returns:
        The response from the Elasticsearch update operation.
    """
    
    # Create, validate, and dump model
    doc_partial = WorkspaceUpdate.model_validate(doc_partial, context={"user": user, "via": via}).serialize()
    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("workspaces", doc_partial)
    
    # Submit
    client = es_client if es_client is not None else es("studio")
    es_response = client.update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_partial,
        refresh=True
    )
    return es_response

def delete(_id: str, es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
    """Delete a workspace and its associated assets.

    This deletes the workspace and all displays, scenarios, judgements, 
    strategies, benchmarks, and evaluations linked to it.

    Args:
        _id: The UUID of the workspace to delete.

    Returns:
        The response from the Elasticsearch delete_by_query operation.
    """
    body = {
        "query": {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-workspaces" }},
                                { "term": { "_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-displays" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-scenarios" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-judgements" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-strategies" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-benchmarks" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-evaluations" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
    client = es_client if es_client is not None else es("studio")
    es_response = client.delete_by_query(
        index=",".join([
            "esrs-workspaces",
            "esrs-displays",
            "esrs-scenarios",
            "esrs-judgements",
            "esrs-strategies",
            "esrs-benchmarks",
            "esrs-evaluations",
        ]),
        body=body,
        refresh=True,
        conflicts="proceed",
    )
    return es_response