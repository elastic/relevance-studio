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
from ..models import StrategyCreate, StrategyUpdate
from ..models.hyperparameters import check_value_type, value_is_testable

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch

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
        "strategies", workspace_id, text, filters, sort, size, page,
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
    client = es("studio")
    es_response = client.get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(docs: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """Create one or more strategies.

    Accepts a list of strategy data; each item may include an optional `_id`
    for idempotence. Each item is validated independently, so a validation
    failure on one item does not prevent the others from being created.
    Returns a single Elasticsearch `_bulk` response (one `refresh=True` for
    the whole batch, not one per item) with per-item results reported in
    `items`, in the same order as submitted.

    Args:
        docs: A list of strategy data to create.
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
            doc = StrategyCreate.model_validate(doc, context={"user": user, "via": via}).serialize()
        except ValidationError as e:
            synthetic_items[i] = utils.bulk_error_item("index", INDEX_NAME, _id, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc = utils.copy_fields_to_search("strategies", doc)

        operations.append({ "index": { "_index": INDEX_NAME, "_id": _id }})
        operations.append(doc)

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(docs))

def update(docs: List[Dict[str, Any]], user: str = None, via: str = None) -> Dict[str, Any]:
    """Update one or more strategies.

    Accepts a list of partial strategy data; each item must carry its own
    `_id`. Each item is validated independently, so a validation failure on
    one item does not prevent the others from being updated. Returns a
    single Elasticsearch `_bulk` response (one `refresh=True` for the whole
    batch, not one per item) with per-item results reported in `items`, in
    the same order as submitted.

    Args:
        docs: A list of partial strategy data to update, each including `_id`.
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
            doc_partial = StrategyUpdate.model_validate(doc_partial, context={"user": user, "via": via}).serialize()
        except ValidationError as e:
            synthetic_items[i] = utils.bulk_error_item("update", INDEX_NAME, _id, 400, str(e))
            continue

        # Copy searchable fields to _search
        doc_partial = utils.copy_fields_to_search("strategies", doc_partial)

        operations.append({ "update": { "_index": INDEX_NAME, "_id": _id }})
        operations.append({ "doc": doc_partial })

    # Submit
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, synthetic_items, len(docs))

def delete(ids: List[str]) -> Dict[str, Any]:
    """Delete one or more strategies by their _ids.

    Args:
        ids: A list of strategy UUIDs to delete.

    Returns:
        The response from the Elasticsearch bulk delete operation.
    """
    utils.assert_batch_size(ids)
    operations = [{ "delete": { "_index": INDEX_NAME, "_id": _id }} for _id in ids]
    client = es("studio")
    es_response = client.bulk(operations=operations, refresh=True) if operations else { "took": 0, "errors": False, "items": [] }
    return utils.merge_bulk_results(es_response, {}, len(ids))

####  Hyperparameters: render and promote  #####################################

def render(
        _id: Optional[str] = None,
        template: Optional[Dict[str, Any]] = None,
        hyperparameters: Optional[List[Dict[str, Any]]] = None,
        values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
    """Render a strategy template with its hyperparameter values applied.

    Substitutes only the `{{hp.*}}` tags and leaves every other Mustache
    variable (e.g. `{{text}}`) in place, so the result is a search template
    ready to copy into production. Give either the `_id` of a saved strategy,
    or a `template` ({source}) with its `hyperparameters`. Hyperparameters
    without an entry in `values` use their promoted values.

    Args:
        _id: The UUID of a saved strategy.
        template: A template object with a `source`, instead of `_id`.
        hyperparameters: The hyperparameter definitions, instead of `_id`.
        values: Hyperparameter values by name, overriding the promoted values.

    Returns:
        {"source": the rendered template source, "values": the values applied}.
    """
    if _id:
        doc = get(_id)["_source"]
        template = doc.get("template") or {}
        hyperparameters = doc.get("hyperparameters") or []
    if not template or "source" not in template:
        raise ValueError("a template with a source is required")
    defs = { h["name"]: h for h in (hyperparameters or []) }
    applied = { name: h["promoted_value"] for name, h in defs.items() }
    for name, value in (values or {}).items():
        if name not in defs:
            raise ValueError(f"'{name}' is not a defined hyperparameter")
        if not check_value_type(defs[name]["type"], value):
            raise ValueError(f"value {value!r} is not a valid {defs[name]['type']} for '{name}'")
        applied[name] = value
    refs = utils.extract_hyperparameter_refs(template["source"])
    undefined = [ n for n in refs if n not in applied ]
    if undefined:
        raise ValueError("template references undefined hyperparameters: " + ", ".join(undefined))
    return {
        "source": utils.render_hyperparameters(template["source"], applied),
        "values": applied,
    }

def promote(
        run_id: str,
        variant_id: str,
        mode: str = "update_values",
        strategy_id: Optional[str] = None,
        name: Optional[str] = None,
        user: str = None,
        via: str = None,
    ) -> Dict[str, Any]:
    """Promote a hyperparameter variant of a run back into a strategy.

    Variants aren't stored as strategies. Promoting one makes it the starting
    point of the next round of iteration. The winning variant is the usual
    choice, but any variant can be promoted (e.g. a slightly lower scoring
    variant with half the latency). Two modes:

      * `update_values`: set the promoted values of the strategy's
        hyperparameters to the variant's values. Edits the current strategy,
        and warns if its template changed since the run.
      * `fork`: create a new strategy from the strategy as it was in the run
        (same template, tags, hyperparameter definitions, and valid testable
        values), with the variant's values as its promoted values.

    Either way, the strategy keeps its hyperparameter definitions and valid
    testable values, so the next round can tune around the new promoted
    values. The strategy records where its promoted values came from in
    `promoted_from`.

    Args:
        run_id: The UUID of the run that tested the variant.
        variant_id: The `variant_id` to promote.
        mode: `update_values` or `fork`.
        strategy_id: The _id of the strategy that was tested. Needed only if
            two strategies of the run share the variant ID.
        name: Name of the new strategy for `fork`. Defaults to the source
            name plus the variant ID.
        user: The username of the requester.

    Returns:
        {"mode", "strategy_id" (the updated or new strategy), "promoted_from",
        "warnings", "response" (the Elasticsearch bulk response)}.
    """
    from . import runs  # imported here to keep the module graph acyclic
    if mode not in ("update_values", "fork"):
        raise ValueError("mode must be 'update_values' or 'fork'")
    variant = runs.get_variant(run_id, variant_id, strategy_id)
    source_id = variant["strategy_id"]
    snapshot = runs.get_runtime_strategy(run_id, source_id)["item"]
    values = variant.get("values") or {}
    defs_in_run = snapshot.get("hyperparameters") or []
    warnings: List[str] = []
    workspace_id = variant["workspace_id"]

    def with_promoted_values(definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for h in definitions:
            h = dict(h)
            if h["name"] in values:
                h["promoted_value"] = values[h["name"]]
            out.append(h)
        return out

    promoted_from = {
        "strategy_id": source_id,
        "run_id": run_id,
        "variant_id": variant_id,
        "values": values,
        "promoted_at": utils.timestamp(),
    }

    if mode == "update_values":
        current = get(source_id)["_source"]
        current_defs = { h["name"]: h for h in (current.get("hyperparameters") or []) }
        for hp_name, value in values.items():
            if hp_name not in current_defs:
                raise ValueError(f"the strategy no longer defines hyperparameter '{hp_name}'")
            if not check_value_type(current_defs[hp_name]["type"], value):
                raise ValueError(
                    f"hyperparameter '{hp_name}' is now a {current_defs[hp_name]['type']}, "
                    f"so the value {value!r} no longer fits"
                )
            if not value_is_testable(
                current_defs[hp_name]["type"], value, current_defs[hp_name].get("testable_values")
            ):
                raise ValueError(
                    f"the value {value!r} is no longer one of the valid testable values "
                    f"of hyperparameter '{hp_name}'"
                )
        if utils.fingerprint([ (current.get("template") or {}).get("source") ]) != snapshot.get("_fingerprint"):
            warnings.append("The strategy's template changed since the run. The promoted values may not suit it.")
        response = update([{
            "_id": source_id,
            "workspace_id": workspace_id,
            "hyperparameters": with_promoted_values(current.get("hyperparameters") or []),
            "promoted_from": promoted_from,
        }], user=user, via=via)
        target_id = source_id
    else:
        target_id = utils.unique_id()
        response = create([{
            "_id": target_id,
            "workspace_id": workspace_id,
            "name": name or f"{snapshot.get('name', 'Strategy')} ({variant_id[:8]})",
            "tags": snapshot.get("tags") or [],
            "template": snapshot.get("template") or {},
            "hyperparameters": with_promoted_values(defs_in_run),
            "promoted_from": promoted_from,
        }], user=user, via=via)

    items = response.get("items") or []
    first = items[0] if items else {}
    result_item = next(iter(first.values()), {}) if first else {}
    if response.get("errors") or (result_item.get("status") or 200) >= 300:
        raise ValueError(f"promotion failed: {result_item.get('error') or response}")
    return {
        "mode": mode,
        "strategy_id": target_id,
        "promoted_from": promoted_from,
        "warnings": warnings,
        "response": response,
    }
