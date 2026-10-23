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
from ..models import DisplayCreate, DisplayUpdate

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch

INDEX_NAME = "esrs-displays"

def search(
        workspace_id: str,
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """Search for displays.

    Args:
        workspace_id: The UUID of the workspace.
        text: Search text for filtering displays.
        filters: List of additional Elasticsearch filters.
        sort: Sorting configuration for the search.
        size: Number of displays to return per page.
        page: Page number for pagination.
        aggs: Whether to include aggregations.

    Returns:
        A dictionary containing the search results.
    """
    response = utils.search_assets(
        "displays", workspace_id, text, filters, sort, size, page,
    )
    return response

def get(_id: str) -> Dict[str, Any]:
    """Get a display by its _id.

    Args:
        _id: The UUID of the display.

    Returns:
        The display document from Elasticsearch.
    """
    client = es("studio")
    es_response = client.get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(docs: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """Create one or more displays.

    Accepts a list of display data; each item may include an optional `_id`
    for idempotence. Each item is validated independently, so a validation
    failure on one item does not prevent the others from being created.
    Returns a single Elasticsearch `_bulk` response (one `refresh=True` for
    the whole batch, not one per item) with per-item results reported in
    `items`, in the same order as submitted.

    Args:
        docs: A list of display data to create.
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
            doc = DisplayCreate.model_validate(doc, context={"user": user, "via": via}).serialize()
        except ValidationError as e:
            synthetic_items[i] = utils.bulk_error_item("index", INDEX_NAME, _id, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc = utils.copy_fields_to_search("displays", doc)

        operations.append({ "index": { "_index": INDEX_NAME, "_id": _id }})
        operations.append(doc)

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(docs))

def update(docs: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """Update one or more displays.

    Accepts a list of partial display data; each item must carry its own
    `_id`. Each item is validated independently, so a validation failure on
    one item does not prevent the others from being updated. Returns a
    single Elasticsearch `_bulk` response (one `refresh=True` for the whole
    batch, not one per item) with per-item results reported in `items`, in
    the same order as submitted.

    Args:
        docs: A list of partial display data to update, each including `_id`.
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
            doc_partial = DisplayUpdate.model_validate(doc_partial, context={"user": user, "via": via}).serialize()
        except ValidationError as e:
            synthetic_items[i] = utils.bulk_error_item("update", INDEX_NAME, _id, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc_partial = utils.copy_fields_to_search("displays", doc_partial)

        operations.append({ "update": { "_index": INDEX_NAME, "_id": _id }})
        operations.append({ "doc": doc_partial })

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(docs))

def delete(ids: List[str]) -> Dict[str, Any]:
    """Delete one or more displays by their _ids.

    Args:
        ids: A list of display UUIDs to delete.

    Returns:
        The response from the Elasticsearch bulk delete operation.
    """
    utils.assert_batch_size(ids)
    operations = [{ "delete": { "_index": INDEX_NAME, "_id": _id }} for _id in ids]
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, {}, len(ids))