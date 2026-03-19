# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import ScenarioCreate, ScenarioUpdate

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
        counts=[ "judgements" ] if aggs else []
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
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: Dict[str, Any], user: str = None) -> Dict[str, Any]:
    """
    Create a scenario. Generates a deterministic _id for UX efficiency, and
    to prevent the creation of duplicate scenarios for the same values.

    Args:
        doc: The scenario data to create.
        user: The username of the creator.

    Returns:
        The response from the Elasticsearch index operation.
    """
    
    # Create, validate, and dump model
    doc = ScenarioCreate.model_validate(doc, context={"user": user}).serialize()

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("scenarios", doc)
    
    # Submit
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id([ doc["workspace_id"], doc["values"] ]),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any], user: str = None) -> Dict[str, Any]:
    """Update a scenario by its _id.

    Args:
        _id: The UUID of the scenario.
        doc_partial: The partial scenario data to update.
        user: The username of the updater.

    Returns:
        The response from the Elasticsearch update operation.
    """
    
    # Create, validate, and dump model
    doc_partial = ScenarioUpdate.model_validate(doc_partial, context={"user": user}).serialize()
    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("scenarios", doc_partial)
    
    # Submit
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_partial,
        refresh=True
    )
    return es_response

def delete(_id: str) -> Dict[str, Any]:
    """Delete a scenario and its associated judgements.

    Args:
        _id: The UUID of the scenario to delete.

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
                                { "term": { "_index": "esrs-scenarios" }},
                                { "term": { "_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-judgements" }},
                                { "term": { "scenario_id": _id }}
                            ]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
    es_response = es("studio").delete_by_query(
        index="esrs-scenarios,esrs-judgements",
        body=body,
        refresh=True,
        conflicts="proceed",
    )
    return es_response