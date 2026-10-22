# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""Reindex-and-cutover transforms for the v2.0 benchmark-run storage split.

This module performs the one-time data migration that splits the monolithic
``esrs-evaluations`` document into many stores:

  * ``esrs-benchmark-runs``      (plain index)  — one doc per run (1:1)
  * ``esrs-benchmark-results``   (data stream)  — one doc per (run x strategy x
                                                  scenario) search (1:N fan-out)
  * ``esrs-benchmark-runtime-{indices,strategies,scenarios,judgements}``
                                 (data streams) — one doc per runtime item,
                                                  so each collection paginates
                                                  independently (judgements in
                                                  particular scale with rated docs)
  * ``esrs-benchmark-unrated-docs`` (data stream) — one doc per unrated document
  * ``esrs-benchmark-failures``     (data stream) — one doc per strategy failure

and renames ``esrs-benchmarks`` -> ``esrs-benchmark-configs`` (1:1 copy).

Why Python instead of the Elasticsearch ``_reindex`` API: ``_reindex`` is
strictly one-source-doc -> one-dest-doc, so the per-item fan-outs (one run -> N
rows) are impossible with a reindex script. A single ``helpers.bulk`` pass over
the source, fanning out in Python, handles every destination uniformly and lets
us assign deterministic ``_id`` values for retry-safety.

Retry-safety: data streams are append-only (``op_type: create`` only), so a
partial failure followed by a retry would duplicate every already-written doc
if ``_id`` were system-generated. We instead derive a deterministic ``_id`` per
destination doc; a retry then re-attempts the same ``_id`` and Elasticsearch
returns a 409 ``version_conflict_engine_exception`` for the already-written
docs, which we treat as success. This makes the migration idempotent.
"""

# Standard packages
from typing import Any, Dict, Iterator, List, Optional, Tuple

# Elastic packages
from elasticsearch import helpers
from elasticsearch.exceptions import NotFoundError

# App packages
from ..client import es
from .. import utils

# Page size for the platform-agnostic search_after iterator. We avoid the
# scroll API entirely (helpers.scan uses scroll, which is unavailable on
# Serverless) by paging with a point-in-time + search_after where available,
# falling back to a plain sized search_after otherwise.
_PAGE_SIZE = 500


def _iter_source_docs(client, source_index: str) -> Iterator[Dict[str, Any]]:
    """Yield every document in ``source_index`` as ``{"_id", "_source"}``.

    Platform-agnostic: uses ``search_after`` paging sorted by ``_shard_doc``
    over a point-in-time when the deployment supports PITs, else a plain
    ``search_after`` on ``_doc``. Neither path uses the scroll API, so this
    works identically on self-managed, ECH, and Serverless.
    """
    # Nothing to iterate if the source index/data stream does not exist
    # (e.g. a fresh v2.0 install with no v1 data to migrate).
    if not client.indices.exists(index=source_index):
        return

    pit_id: Optional[str] = None
    try:
        pit = client.open_point_in_time(index=source_index, keep_alive="2m")
        pit_id = pit.get("id")
    except Exception:
        pit_id = None

    search_after: Optional[List[Any]] = None
    try:
        while True:
            body: Dict[str, Any] = {
                "size": _PAGE_SIZE,
                "query": {"match_all": {}},
                "sort": [{"_shard_doc": "asc"}] if pit_id else [{"_doc": "asc"}],
            }
            if pit_id:
                body["pit"] = {"id": pit_id, "keep_alive": "2m"}
            if search_after is not None:
                body["search_after"] = search_after

            # When using a PIT, the index must not be passed separately.
            if pit_id:
                response = client.search(body=body)
            else:
                response = client.search(index=source_index, body=body)

            hits = response.body.get("hits", {}).get("hits", [])
            if not hits:
                break
            for hit in hits:
                yield {"_id": hit["_id"], "_source": hit.get("_source", {})}
            search_after = hits[-1].get("sort")
            if search_after is None:
                break
            # Carry forward the PIT id, which may be refreshed each page.
            if pit_id:
                pit_id = response.body.get("pit_id", pit_id)
    finally:
        if pit_id:
            try:
                client.close_point_in_time(body={"id": pit_id})
            except Exception:
                pass


def _timestamp_for(source: Dict[str, Any]) -> str:
    """@timestamp for a data-stream doc: the run's stopped_at, else write-time."""
    meta = source.get("@meta") or {}
    return meta.get("stopped_at") or utils.timestamp()


def _transform_configs(hit: Dict[str, Any], dest: str) -> List[Dict[str, Any]]:
    """esrs-benchmarks -> esrs-benchmark-configs (1:1 copy, same _id)."""
    return [{
        "_op_type": "index",
        "_index": dest,
        "_id": hit["_id"],
        "_source": hit["_source"],
    }]


def _transform_runs(hit: Dict[str, Any], dest: str) -> List[Dict[str, Any]]:
    """esrs-evaluations -> esrs-benchmark-runs (1:1), stripping heavy fields."""
    src = dict(hit["_source"])
    for heavy in ("results", "runtime", "unrated_docs"):
        src.pop(heavy, None)
    return [{
        "_op_type": "index",
        "_index": dest,
        "_id": hit["_id"],
        "_source": src,
    }]


def _transform_results(hit: Dict[str, Any], dest: str) -> List[Dict[str, Any]]:
    """esrs-evaluations -> esrs-benchmark-results (1:N fan-out, one per search).

    Flattens the nested ``results[].searches[]`` structure into one document
    per (run_id, strategy_id, scenario_id) with a deterministic ``_id``.
    """
    src = hit["_source"]
    run_id = hit["_id"]
    ts = _timestamp_for(src)
    workspace_id = src.get("workspace_id")
    benchmark_id = src.get("benchmark_id")
    docs: List[Dict[str, Any]] = []
    for result in (src.get("results") or []):
        strategy_id = result.get("strategy_id")
        for search in (result.get("searches") or []):
            scenario_id = search.get("scenario_id")
            row = {
                "run_id": run_id,
                "workspace_id": workspace_id,
                "benchmark_id": benchmark_id,
                "strategy_id": strategy_id,
                "scenario_id": scenario_id,
                "metrics": search.get("metrics"),
                "hits": search.get("hits"),
                "@timestamp": ts,
            }
            docs.append({
                "_op_type": "create",
                "_index": dest,
                "_id": utils.unique_id([run_id, strategy_id, scenario_id]),
                "_source": {k: v for k, v in row.items() if v is not None},
            })
    return docs


def _forensics_base(hit: Dict[str, Any]) -> Dict[str, Any]:
    src = hit["_source"]
    return {
        "run_id": hit["_id"],
        "workspace_id": src.get("workspace_id"),
        "benchmark_id": src.get("benchmark_id"),
        "@timestamp": _timestamp_for(src),
    }


def _transform_runtime_collection(hit: Dict[str, Any], dest: str, runtime_key: str, id_field: str) -> List[Dict[str, Any]]:
    """esrs-evaluations -> one per-item doc per entry in runtime[runtime_key]."""
    src = hit["_source"]
    run_id = hit["_id"]
    base = _forensics_base(hit)
    docs = []
    for item_key, item_value in ((src.get("runtime") or {}).get(runtime_key) or {}).items():
        doc = {**base, id_field: item_key, "item": item_value}
        if runtime_key == "judgements" and isinstance(item_value, dict) and item_value.get("scenario_id"):
            doc["scenario_id"] = item_value["scenario_id"]
        if runtime_key in ("strategies", "scenarios") and isinstance(item_value, dict):
            if item_value.get("name"):
                doc["name"] = item_value["name"]
            if item_value.get("tags"):
                doc["tags"] = item_value["tags"]
        docs.append({
            "_op_type": "create",
            "_index": dest,
            "_id": utils.unique_id([run_id, runtime_key, item_key]),
            "_source": doc,
        })
    return docs


def _transform_runtime_indices(hit, dest):
    return _transform_runtime_collection(hit, dest, "indices", "index")

def _transform_runtime_strategies(hit, dest):
    return _transform_runtime_collection(hit, dest, "strategies", "strategy_id")

def _transform_runtime_scenarios(hit, dest):
    return _transform_runtime_collection(hit, dest, "scenarios", "scenario_id")

def _transform_runtime_judgements(hit, dest):
    return _transform_runtime_collection(hit, dest, "judgements", "judgement_id")


def _transform_unrated_docs(hit: Dict[str, Any], dest: str) -> List[Dict[str, Any]]:
    """esrs-evaluations -> one doc per unrated document."""
    src = hit["_source"]
    run_id = hit["_id"]
    base = _forensics_base(hit)
    docs = []
    for u in (src.get("unrated_docs") or []):
        docs.append({
            "_op_type": "create",
            "_index": dest,
            "_id": utils.unique_id([run_id, "unrated", u.get("_index"), u.get("_id")]),
            "_source": {
                **base,
                "doc_id": u.get("_id"),
                "doc_index": u.get("_index"),
                "count": u.get("count"),
                "strategies": u.get("strategies") or [],
                "scenarios": u.get("scenarios") or [],
            },
        })
    return docs


def _transform_failures(hit: Dict[str, Any], dest: str) -> List[Dict[str, Any]]:
    """esrs-evaluations -> one doc per strategy that had failures."""
    src = hit["_source"]
    run_id = hit["_id"]
    base = _forensics_base(hit)
    docs = []
    for r in (src.get("results") or []):
        if not r.get("failures"):
            continue
        strategy_id = r.get("strategy_id")
        docs.append({
            "_op_type": "create",
            "_index": dest,
            "_id": utils.unique_id([run_id, "failures", strategy_id]),
            "_source": {**base, "strategy_id": strategy_id, "failures": r.get("failures")},
        })
    return docs


_TRANSFORMS = {
    "copy": _transform_configs,
    "runs": _transform_runs,
    "results": _transform_results,
    "runtime_indices": _transform_runtime_indices,
    "runtime_strategies": _transform_runtime_strategies,
    "runtime_scenarios": _transform_runtime_scenarios,
    "runtime_judgements": _transform_runtime_judgements,
    "unrated_docs": _transform_unrated_docs,
    "failures": _transform_failures,
}


def _is_version_conflict(error: Dict[str, Any]) -> bool:
    """True if a bulk item error is a benign already-exists conflict."""
    info = error.get("create", error.get("index", {})) if isinstance(error, dict) else {}
    if info.get("status") == 409:
        return True
    err = info.get("error", {})
    return isinstance(err, dict) and err.get("type") == "version_conflict_engine_exception"


def run_reindex_transform(source_index: str, dest_index: str, mode: str) -> Dict[str, Any]:
    """Copy/split ``source_index`` into ``dest_index`` using ``mode``.

    ``mode`` is one of ``copy`` (configs), ``runs``, ``results``,
    ``runtime_indices``, ``runtime_strategies``, ``runtime_scenarios``,
    ``runtime_judgements``, ``unrated_docs``, ``failures``.
    Returns a summary ``{expected, written, conflicts, errors}`` where
    ``expected`` is the number of destination docs the transform intended to
    write (used for fan-out-aware count verification), ``conflicts`` are benign
    already-exists 409s (idempotent re-runs), and ``errors`` are real failures.
    """
    if mode not in _TRANSFORMS:
        raise ValueError(f"Unknown reindex mode '{mode}'.")
    transform = _TRANSFORMS[mode]
    client = es("studio")

    expected = 0
    actions: List[Dict[str, Any]] = []

    def _action_stream() -> Iterator[Dict[str, Any]]:
        nonlocal expected
        for hit in _iter_source_docs(client, source_index):
            for action in transform(hit, dest_index):
                expected += 1
                yield action

    written = 0
    conflicts = 0
    errors: List[Dict[str, Any]] = []
    # raise_on_error=False so benign 409 conflicts (idempotent retries) do not
    # abort the migration; we classify them ourselves below.
    for ok, item in helpers.streaming_bulk(
        client,
        _action_stream(),
        raise_on_error=False,
        refresh="wait_for",
        max_retries=3,
    ):
        if ok:
            written += 1
        elif _is_version_conflict(item):
            conflicts += 1
        else:
            errors.append(item)

    return {
        "expected": expected,
        "written": written,
        "conflicts": conflicts,
        "errors": errors[:10],  # cap for response payload size
        "error_count": len(errors),
    }
