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
    )
    return response

def get(_id: str, user: Optional[str] = None) -> Dict[str, Any]:
    """Get a conversation by its _id.

    Args:
        _id: The UUID of the conversation.

    Returns:
        The conversation document from Elasticsearch.
    """
    client = es("studio")
    es_response = client.get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    _assert_owner(es_response, user)
    return es_response

def create(doc: Dict[str, Any], _id: str = None, user: str = None, via: str = None) -> Dict[str, Any]:
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
    client = es("studio")
    es_response = client.index(
        index=INDEX_NAME,
        id=_id,
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any], user: str = None, via: str = None, refresh: bool = True) -> Dict[str, Any]:
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
    
    client = es("studio")

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

def delete(ids: List[str], user: Optional[str] = None) -> Dict[str, Any]:
    """Delete one or more conversations by their _ids.

    Accepts a list of conversation UUIDs. Ownership is enforced per item: a
    single `mget` checks who owns each id (replacing N individual `get`
    calls), then one `_bulk` call deletes only the ids owned by `user`
    (replacing N individual deletes). Ids that don't exist, or that exist
    but aren't owned by `user`, are reported as per-item failures rather
    than aborting the whole batch — the response never reveals whether a
    denied id exists, only that access to it is denied.

    Args:
        ids: A list of conversation UUIDs to delete.
        user: The username of the caller.

    Returns:
        The response from the Elasticsearch bulk delete operation.
    """
    utils.assert_batch_size(ids)
    client = es("studio")
    mget_response = client.mget(
        index=INDEX_NAME,
        ids=ids,
        source_includes=["@meta.created_by"],
    )
    mget_docs = mget_response.get("docs") or []

    operations = []
    synthetic_items = {}
    for i, (doc, _id) in enumerate(zip(mget_docs, ids)):
        found = bool(doc.get("found"))
        owner = (doc.get("_source") or {}).get("@meta", {}).get("created_by") if found else None
        if found and owner == _normalize_user(user):
            operations.append({ "delete": { "_index": INDEX_NAME, "_id": _id }})
        elif found:
            # Exists, but owned by someone else.
            synthetic_items[i] = utils.bulk_error_item(
                "delete", INDEX_NAME, _id, 403, "Conversation access denied.", "security_exception",
            )
        else:
            # Doesn't exist. Tracked distinctly from "forbidden" only so the
            # single-item Flask route can stay byte-identical to the
            # pre-bulk 404-vs-403 contract; multi-item callers and MCP
            # collapse this into the same 403 shape (see
            # utils.collapse_denial_statuses) to avoid leaking existence.
            synthetic_items[i] = utils.bulk_error_item(
                "delete", INDEX_NAME, _id, 404, f"Conversation [{_id}] not found.", "resource_not_found_exception",
            )

    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(ids))
