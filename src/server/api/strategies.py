# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import StrategyCreate, StrategyUpdate

INDEX_NAME = "esrs-strategies"

def search(
        workspace_id: str,
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """Search for strategies.

    Args:
        workspace_id: The UUID of the workspace.
        text: Search text for filtering strategies.
        filters: List of additional Elasticsearch filters.
        sort: Sorting configuration for the search.
        size: Number of strategies to return per page.
        page: Page number for pagination.
        aggs: Whether to include aggregations.

    Returns:
        A dictionary containing the search results.
    """
    response = utils.search_assets(
        "strategies", workspace_id, text, filters, sort, size, page
    )
    return response

def tags(workspace_id: str) -> Dict[str, Any]:
    """List all strategy tags (up to 10,000).

    Args:
        workspace_id: The UUID of the workspace.

    Returns:
        The response from Elasticsearch containing tag aggregations.
    """
    es_response = utils.search_tags("strategies", workspace_id)
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """Get a strategy by its _id.

    Args:
        _id: The UUID of the strategy.

    Returns:
        The strategy document from Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: Dict[str, Any], _id: str = None, user: str = None) -> Dict[str, Any]:
    """Create a strategy.

    Args:
        doc: The strategy data to create.
        _id: Optional pregenerated UUID for idempotence.
        user: The username of the creator.

    Returns:
        The response from the Elasticsearch index operation.
    """
    
    # Create, validate, and dump model
    doc = StrategyCreate.model_validate(doc, context={"user": user}).serialize()

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("strategies", doc)
    
    # Submit
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any], user: str = None) -> Dict[str, Any]:
    """Update a strategy by its _id.

    Args:
        _id: The UUID of the strategy.
        doc_partial: The partial strategy data to update.
        user: The username of the updater.

    Returns:
        The response from the Elasticsearch update operation.
    """ 
    
    # Create, validate, and dump model
    doc_partial = StrategyUpdate.model_validate(doc_partial, context={"user": user}).serialize()
    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("strategies", doc_partial)
    
    # Submit
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_partial,
        refresh=True
    )
    return es_response

def delete(_id: str) -> Dict[str, Any]:
    """Delete a strategy by its _id.

    Args:
        _id: The UUID of the strategy to delete.

    Returns:
        The response from the Elasticsearch delete operation.
    """
    es_response = es("studio").delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True
    )
    return es_response