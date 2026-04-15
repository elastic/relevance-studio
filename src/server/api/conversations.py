# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# Third-party packages
from werkzeug.exceptions import Forbidden

# App packages
from .. import utils
from ..client import es
from ..models import ConversationsCreate, ConversationsUpdate

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch

INDEX_NAME = "esrs-conversations"


def _normalize_user(user: Optional[str]) -> str:
    return user or "unknown"


def _created_by_filter(user: Optional[str]) -> Dict[str, Dict[str, str]]:
    return {"term": {"@meta.created_by": _normalize_user(user)}}


def _assert_owner(es_response: Any, user: Optional[str]) -> None:
    body = es_response if isinstance(es_response, dict) else getattr(es_response, "body", {}) or {}
    source = body.get("_source", {})
    owner = (source.get("@meta") or {}).get("created_by")
    if owner != _normalize_user(user):
        raise Forbidden("Conversation access denied.")

def search(
        text: str = "",
        filters: Optional[List[Dict[str, Any]]] = None,
        sort: Optional[Dict[str, Any]] = None,
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
        user: Optional[str] = None,
        es_client: Optional["Elasticsearch"] = None,
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
    enforced_filters = [_created_by_filter(user), *(filters or [])]
    response = utils.search_assets(
        "conversations", None, text, enforced_filters, sort or {}, size, page,
        es_client=es_client,
    )
    return response

def get(_id: str, user: Optional[str] = None, source_includes: Optional[List[str]] = None, es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
    """Get a conversation by its _id.

    Args:
        _id: The UUID of the conversation.
        source_includes: Optional list of source fields to return (e.g. ["messages"]).

    Returns:
        The conversation document from Elasticsearch.
    """
    client = es_client if es_client is not None else es("studio")
    # Ensure ownership field is always fetched for the access check
    includes = source_includes
    if includes is not None and user is not None:
        if "@meta.created_by" not in includes:
            includes = list(includes) + ["@meta.created_by"]
    kwargs = dict(index=INDEX_NAME, id=_id, source_excludes="_search")
    if includes is not None:
        kwargs["source_includes"] = includes
    es_response = client.get(**kwargs)
    _assert_owner(es_response, user)
    return es_response

def create(doc: Dict[str, Any], _id: str = None, user: str = None, via: str = None, es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
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
    doc = ConversationsCreate.model_validate(doc, context={"user": user, "via": via}).serialize()

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("conversations", doc)
    
    # Submit
    client = es_client if es_client is not None else es("studio")
    es_response = client.index(
        index=INDEX_NAME,
        id=_id,
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any], user: str = None, via: str = None, refresh: bool = True, es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
    """Update a conversation by its _id.

    Args:
        _id: The UUID of the conversation.
        doc_partial: The partial conversation data to update.
        user: The username of the updater.
        refresh: Whether to refresh the index immediately. Default True for 
                 backward compatibility. Set to False for high-frequency updates
                 during agent streaming.

    Returns:
        The response from the Elasticsearch update operation.
    """
    
    client = es_client if es_client is not None else es("studio")

    # Verify the caller owns the conversation before mutating it.
    owner_check = client.get(
        index=INDEX_NAME,
        id=_id,
        source_includes=["@meta.created_by"],
        source_excludes="_search",
    )
    _assert_owner(owner_check, user)

    # Create, validate, and dump model
    doc_partial = ConversationsUpdate.model_validate(doc_partial, context={"user": user, "via": via}).serialize()

    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("conversations", doc_partial)
    
    # Submit
    es_response = client.update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_partial,
        refresh=refresh
    )
    return es_response

def delete(_id: str, user: Optional[str] = None, es_client: Optional["Elasticsearch"] = None) -> Dict[str, Any]:
    """Delete a conversation by its _id.

    Args:
        _id: The UUID of the conversation to delete.

    Returns:
        The response from the Elasticsearch delete operation.
    """
    client = es_client if es_client is not None else es("studio")
    owner_check = client.get(
        index=INDEX_NAME,
        id=_id,
        source_includes=["@meta.created_by"],
        source_excludes="_search",
    )
    _assert_owner(owner_check, user)
    es_response = client.delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True,
    )
    return es_response
