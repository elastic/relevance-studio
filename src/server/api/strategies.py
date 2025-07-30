# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

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
    """
    Search for strategies.
    """
    response = utils.search_assets(
        "strategies", workspace_id, text, filters, sort, size, page
    )
    return response

def tags(workspace_id: str) -> Dict[str, Any]:
    """
    List all strategy tags (up to 10,000).
    """
    es_response = utils.search_tags("strategies", workspace_id)
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a strategy by its _id.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: Dict[str, Any], _id: str = None, user: str = None) -> Dict[str, Any]:
    """
    Create a strategy.
    
    Accepts an optional pregenerated _id for idempotence.
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
    """
    Update a strategy by its _id.
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
    """
    Delete a strategy by its _id.
    """
    es_response = es("studio").delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True
    )
    return es_response