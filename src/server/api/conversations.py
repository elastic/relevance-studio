# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import ConversationsCreate, ConversationsUpdate

INDEX_NAME = "esrs-conversations"

def search(
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """Search for conversations.

    Args:
        text: Search text for filtering conversations.
        filters: List of additional Elasticsearch filters.
        sort: Sorting configuration for the search.
        size: Number of conversations to return per page.
        page: Page number for pagination.
        aggs: Whether to include aggregations.

    Returns:
        A dictionary containing the search results.
    """
    response = utils.search_assets(
        "conversations", None, text, filters, sort, size, page
    )
    return response

def get(_id: str) -> Dict[str, Any]:
    """Get a conversation by its _id.

    Args:
        _id: The UUID of the conversation.

    Returns:
        The conversation document from Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: Dict[str, Any], _id: str = None, user: str = None) -> Dict[str, Any]:
    """Create a conversation.

    Args:
        doc: The conversation data to create.
        _id: Optional pregenerated UUID for idempotence.
        user: The username of the creator.

    Returns:
        The response from the Elasticsearch index operation.
    """
    
    # Ensure conversation_id is consistent with _id
    if _id:
        doc["conversation_id"] = _id
    elif "conversation_id" in doc:
        _id = doc["conversation_id"]
    else:
        _id = utils.unique_id()
        doc["conversation_id"] = _id

    # Remove deprecated plain 'id' field if present
    doc.pop("id", None)

    # Create, validate, and dump model
    doc = ConversationsCreate.model_validate(doc, context={"user": user}).serialize()

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("conversations", doc)
    
    # Submit
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id,
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any], user: str = None) -> Dict[str, Any]:
    """Update a conversation by its _id.

    Args:
        _id: The UUID of the conversation.
        doc_partial: The partial conversation data to update.
        user: The username of the updater.

    Returns:
        The response from the Elasticsearch update operation.
    """
    
    # Create, validate, and dump model
    doc_partial = ConversationsUpdate.model_validate(doc_partial, context={"user": user}).serialize()

    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("conversations", doc_partial)
    
    # Submit
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_partial,
        refresh=True
    )
    return es_response

def delete(_id: str) -> Dict[str, Any]:
    """Delete a conversation by its _id.

    Args:
        _id: The UUID of the conversation to delete.

    Returns:
        The response from the Elasticsearch delete operation.
    """
    es_response = es("studio").delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True,
    )
    return es_response
