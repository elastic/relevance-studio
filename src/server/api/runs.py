# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import itertools
import os
import time
import traceback
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

# Elastic packages
from elastic_transport import ConnectionError, ConnectionTimeout
from elasticsearch import ApiError
from elasticsearch.exceptions import NotFoundError

# App packages
from . import benchmarks, content, optimization
from .. import utils
from ..client import es

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch
from ..models.benchmarks import TaskCreate
from ..models.hyperparameters import Optimization
from ..models import (
    RunComplete,
    RunCreate,
    RunFail,
    RunSkip,
    BenchmarkResult,
)
from elasticsearch import helpers

INDEX_NAME = "esrs-benchmark-runs"
CONFIGS_INDEX_NAME = "esrs-benchmark-configs"
RESULTS_INDEX_NAME = "esrs-benchmark-results"
RUNTIME_INDICES_INDEX_NAME = "esrs-benchmark-runtime-indices"
RUNTIME_STRATEGIES_INDEX_NAME = "esrs-benchmark-runtime-strategies"
RUNTIME_SCENARIOS_INDEX_NAME = "esrs-benchmark-runtime-scenarios"
RUNTIME_JUDGEMENTS_INDEX_NAME = "esrs-benchmark-runtime-judgements"
UNRATED_DOCS_INDEX_NAME = "esrs-benchmark-unrated-docs"
FAILURES_INDEX_NAME = "esrs-benchmark-failures"
RUNTIME_VARIANTS_INDEX_NAME = "esrs-benchmark-runtime-variants"

# All immutable per-run data streams that hold a run's results + forensics.
# Used by cleanup / delete cascades to sweep everything owned by a run_id.
RUN_DATA_STREAMS = [
    RESULTS_INDEX_NAME,
    RUNTIME_INDICES_INDEX_NAME,
    RUNTIME_STRATEGIES_INDEX_NAME,
    RUNTIME_SCENARIOS_INDEX_NAME,
    RUNTIME_JUDGEMENTS_INDEX_NAME,
    UNRATED_DOCS_INDEX_NAME,
    FAILURES_INDEX_NAME,
    RUNTIME_VARIANTS_INDEX_NAME,
]
SEARCH_FIELDS = utils.get_search_fields_from_mapping("benchmark-runs")
VALID_METRICS = set([ "mrr", "ndcg", "precision", "recall" ])
RANK_EVAL_BATCH_SIZE = int(os.getenv("RANK_EVAL_BATCH_SIZE", "0"))
def _parse_rank_eval_batch_delay_seconds(value: str) -> float:
    """
    Parse RANK_EVAL_BATCH_DELAY from env.

    Supported formats:
      - "1000"   -> 1000ms (default unit)
      - "1000ms" -> 1000ms
      - "1s"     -> 1 second
      - "0.5s"   -> 0.5 second
    """
    raw = str(value or "0").strip().lower()
    if not raw:
        return 0.0
    try:
        if raw.endswith("ms"):
            return max(0.0, float(raw[:-2].strip()) / 1000.0)
        if raw.endswith("s"):
            return max(0.0, float(raw[:-1].strip()))
        # Default unit is milliseconds.
        return max(0.0, float(raw) / 1000.0)
    except ValueError:
        logging.getLogger(__name__).warning(
            "Invalid RANK_EVAL_BATCH_DELAY value '%s'. Falling back to 0ms.",
            value
        )
        return 0.0

RANK_EVAL_BATCH_DELAY_SEC = _parse_rank_eval_batch_delay_seconds(
    os.getenv("RANK_EVAL_BATCH_DELAY", "0")
)

logger = logging.getLogger(__name__)

def _generate_summary_metrics(searches_list):
    """Calculate aggregated metrics from a list of search results.

    Args:
        searches_list: A list of search result dictionaries containing hits and metrics.

    Returns:
        A dictionary containing aggregated 'metrics', 'unrated_docs', and 'took'
        statistics.
    """
    metrics = {}
    unrated_count = 0
    total_hits = 0
    
    # Group metrics by metric name
    metric_values = {}
    # "took" (ms to run the search) is only present in Elasticsearch 9.6.0+
    # rank_eval responses; collect only the values that are actually present
    # so older clusters (where no search reports `took`) yield an empty list
    # rather than a misleading average of zeros.
    took_values = []
    for search in searches_list:
        # Count unrated documents from hits
        if 'hits' in search:
            for hit_data in search['hits']:
                total_hits += 1
                if hit_data.get('rating') is None:
                    unrated_count += 1
        
        # Collect metric values
        if 'metrics' in search:
            for metric_name, value in search['metrics'].items():
                if metric_name not in metric_values:
                    metric_values[metric_name] = []
                metric_values[metric_name].append(value)

        # Collect "took" values
        if search.get('took') is not None:
            took_values.append(search['took'])
    
    # Calculate aggregated metrics
    for metric_name, values in metric_values.items():
        if values:
            metrics[metric_name] = {
                'avg': sum(values) / len(values),
                'max': max(values),
                'min': min(values)
            }
    
    # Calculate unrated docs stats
    unrated_docs = {
        'count': unrated_count,
        'percent': (unrated_count / total_hits * 100) if total_hits > 0 else 0.0
    }

    # Calculate "took" stats. `avg` is None when no search in this group
    # reported a `took` value (e.g. against Elasticsearch < 9.6.0).
    took = {
        'avg': (sum(took_values) / len(took_values)) if took_values else None
    }

    return {
        'metrics': metrics,
        'unrated_docs': unrated_docs,
        'took': took
    }

def generate_summary(evaluation, strategies: List, scenarios: List):
    """Generate summary statistics from evaluation results.

    Args:
        evaluation: The evaluation data including results.
        strategies: List of strategies used in the evaluation.
        scenarios: List of scenarios used in the evaluation.

    Returns:
        A dictionary containing summary statistics grouped by strategy ID and tag.
    """
    
    # Initialize summary structure
    summary = {
        'strategy_id': {},
        'strategy_tag': {}
    }
    
    # Get all unique _ids scenarios in results
    strategy_ids = set()
    scenario_ids = set()
    for result in evaluation['results']:
        strategy_ids.add(result['strategy_id'])
        for search in result['searches']:
            scenario_ids.add(search['scenario_id'])
    
    # Get all unique strategy tags and scenario tags from results
    strategy_tags = set()
    scenario_tags = set()
    strategy_id_to_tags = {}
    for s in strategies:
        tags = s.get("tags", [])
        strategy_tags.update(tags)
        strategy_id_to_tags[s["_id"]] = tags
    
    scenario_id_to_tags = {}
    for s in scenarios:
        tags = s.get("tags", [])
        scenario_tags.update(tags)
        scenario_id_to_tags[s["_id"]] = tags

    strategy_tags = sorted(strategy_tags)
    scenario_tags = sorted(scenario_tags)
    
    # Process by strategy _id
    for strategy_id in strategy_ids:
        strategy_results = [
            r for r in evaluation['results'] if r['strategy_id'] == strategy_id
        ]
        if not strategy_results:
            continue
        all_searches = []
        for result in strategy_results:
            all_searches.extend(result['searches'])
        
        # Calculate _total metrics
        total_metrics = _generate_summary_metrics(all_searches)
        
        # Calculate by_scenario_id metrics
        by_scenario_id = {}
        for scenario_id in scenario_ids:
            scenario_searches = [
                s for s in all_searches if s['scenario_id'] == scenario_id
            ]
            if scenario_searches:
                by_scenario_id[scenario_id] = _generate_summary_metrics(scenario_searches)
        
        # Calculate by_scenario_tag metrics
        by_scenario_tag = {}
        for scenario_id in scenario_ids:
            scenario_searches = [
                s for s in all_searches if s['scenario_id'] == scenario_id
            ]
            for tag in scenario_id_to_tags.get(scenario_id, []):
                if tag not in by_scenario_tag:
                    by_scenario_tag[tag] = []
                by_scenario_tag[tag].extend(scenario_searches)
        
        # Calculate aggregated metrics for each scenario tag
        for tag in by_scenario_tag:
            by_scenario_tag[tag] = _generate_summary_metrics(by_scenario_tag[tag])

        summary['strategy_id'][strategy_id] = {
            '_total': total_metrics,
            'by_scenario_id': by_scenario_id,
            'by_scenario_tag': by_scenario_tag
        }
    
    # Process by strategy tag
    strategy_tag_searches = {}
    for strategy_id in strategy_ids:
        strategy_results = [
            r for r in evaluation['results'] if r['strategy_id'] == strategy_id
        ]
        for result in strategy_results:
            searches = result['searches']
            for tag in strategy_id_to_tags.get(strategy_id, []):
                if tag not in strategy_tag_searches:
                    strategy_tag_searches[tag] = []
                strategy_tag_searches[tag].extend(searches)
    
    # Calculate metrics for each strategy tag
    for strategy_tag, all_searches in strategy_tag_searches.items():
        # Calculate _total metrics
        total_metrics = _generate_summary_metrics(all_searches)
        
        # Calculate by_scenario_id metrics
        by_scenario_id = {}
        for scenario_id in scenario_ids:
            scenario_searches = [
                s for s in all_searches if s['scenario_id'] == scenario_id
            ]
            if scenario_searches:
                by_scenario_id[scenario_id] = _generate_summary_metrics(scenario_searches)
        
        # Calculate by_scenario_tag metrics
        by_scenario_tag = {}
        for scenario_id in scenario_ids:
            scenario_searches = [
                s for s in all_searches if s['scenario_id'] == scenario_id
            ]
            for tag in scenario_id_to_tags.get(scenario_id, []):
                if tag not in by_scenario_tag:
                    by_scenario_tag[tag] = []
                by_scenario_tag[tag].extend(scenario_searches)
        
        # Calculate aggregated metrics for each scenario tag
        for tag in by_scenario_tag:
            by_scenario_tag[tag] = _generate_summary_metrics(by_scenario_tag[tag])

        summary['strategy_tag'][strategy_tag] = {
            '_total': total_metrics,
            'by_scenario_id': by_scenario_id,
            'by_scenario_tag': by_scenario_tag
        }

    return summary


def _generate_optimization_summary(
        evaluation,
        strategies: List,
        scenarios: List,
        plans: Dict[str, Any],
        outcomes: Dict[str, Any],
        has_holdout: bool,
    ):
    """Generate the run summary from each strategy's winning variant.

    The summary keeps the shape of `generate_summary`, so the run summary table,
    charts, and breakdown work unchanged. `_total` is the headline score: the
    winner's holdout score when the run has a holdout, and its in-sample score
    otherwise. `by_scenario_id` and `by_scenario_tag` cover every scenario of
    the winner. Each strategy also gets an `optimization` block with the winning
    and baseline variants' tuning and holdout scores.
    """
    winner_results = []
    headline_results = []
    for result in evaluation["results"]:
        strategy_id = result["strategy_id"]
        winner_id = outcomes[strategy_id]["winner_id"]
        searches = [ s for s in result["searches"] if s["variant_id"] == winner_id ]
        winner_results.append({ "strategy_id": strategy_id, "searches": searches })
        headline_results.append({
            "strategy_id": strategy_id,
            "searches": [ s for s in searches if s["split"] == "holdout" ] if has_holdout else searches,
        })
    summary = generate_summary({ "results": winner_results }, strategies, scenarios)
    if has_holdout:
        headline = generate_summary({ "results": headline_results }, strategies, scenarios)
        for kind in ("strategy_id", "strategy_tag"):
            for key, value in headline[kind].items():
                if key in summary[kind]:
                    summary[kind][key]["_total"] = value["_total"]

    for result in evaluation["results"]:
        strategy_id = result["strategy_id"]
        if strategy_id not in summary["strategy_id"]:
            continue
        outcome = outcomes[strategy_id]

        def block(variant_id, split):
            searches = [
                s for s in result["searches"]
                if s["variant_id"] == variant_id and s["split"] == split
            ]
            return _generate_summary_metrics(searches) if searches else None

        winner_searches = [ s for s in result["searches"] if s["variant_id"] == outcome["winner_id"] and s["split"] == "tuning" ]
        coverages = [ s["coverage"] for s in winner_searches if s.get("coverage") is not None ]
        summary["strategy_id"][strategy_id]["optimization"] = {
            "variant_id": outcome["winner_id"],
            "baseline_variant_id": outcome["baseline_id"],
            "variant_count": len(plans[strategy_id]["variants"]),
            "no_valid_winner": outcome["no_valid_winner"],
            "score_basis": "holdout" if has_holdout else "in_sample",
            "coverage": sum(coverages) / len(coverages) if coverages else None,
            "tuning": block(outcome["winner_id"], "tuning"),
            "holdout": block(outcome["winner_id"], "holdout"),
            "baseline_tuning": block(outcome["baseline_id"], "tuning"),
            "baseline_holdout": block(outcome["baseline_id"], "holdout"),
        }
    return summary


def _write_results_and_forensics(evaluation: Dict[str, Any], run_id: str) -> None:
    """Persist scored results and the forensics audit doc for a finished run.

    This MUST run before the run doc's terminal status is flipped, so that the
    run doc's @meta.status is the single source of truth for "this run's data is
    complete and trustworthy." If this succeeds and the subsequent terminal
    update fails/crashes, the run is left "running" (not falsely complete) and
    any results/forensics already written are harmless orphans until a stale
    sweep removes them.

    Writes are append-only (op_type: create) into the two data streams, each
    document tagged with run_id + workspace_id + benchmark_id and a populated
    @timestamp (the run's stopped_at). _ids are deterministic so a retry after a
    partial write is idempotent (duplicates return a benign 409).
    """
    client = es("studio")
    workspace_id = evaluation.get("workspace_id")
    benchmark_id = evaluation.get("benchmark_id")
    # @timestamp: the terminal @meta.stopped_at set during model validation,
    # falling back to write-time if somehow absent.
    stopped_at = (evaluation.get("@meta") or {}).get("stopped_at") or utils.timestamp()

    actions: List[Dict[str, Any]] = []

    # One results document per (strategy_id, scenario_id) search, flattening the
    # nested results[].searches[] structure.
    for result in (evaluation.get("results") or []):
        strategy_id = result.get("strategy_id")
        for search in (result.get("searches") or []):
            scenario_id = search.get("scenario_id")
            variant_id = search.get("variant_id")
            split = search.get("split")
            doc = BenchmarkResult.model_validate({
                "run_id": run_id,
                "workspace_id": workspace_id,
                "benchmark_id": benchmark_id,
                "strategy_id": strategy_id,
                "variant_id": variant_id,
                "split": split,
                "scenario_id": scenario_id,
                "metrics": search.get("metrics") or {},
                "hits": search.get("hits") or [],
                "took": search.get("took"),
                "coverage": search.get("coverage"),
                "@timestamp": stopped_at,
            }).serialize()
            actions.append({
                "_op_type": "create",
                "_index": RESULTS_INDEX_NAME,
                "_id": utils.unique_id([run_id, strategy_id, variant_id, split, scenario_id]),
                "_source": doc,
            })

    # Forensics is fanned out into per-item documents across dedicated data
    # streams so each collection can be paginated/queried server-side without
    # ever loading the whole thing (runtime.judgements in particular scales with
    # the number of rated docs). Every document is tagged run_id + workspace_id +
    # benchmark_id + @timestamp, with a deterministic _id for idempotent retries.
    base = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "benchmark_id": benchmark_id,
        "@timestamp": stopped_at,
    }

    def _append_runtime(collection_index: str, id_field: str, runtime_key: str):
        """One doc per entry in evaluation['runtime'][runtime_key] (a dict keyed
        by asset id). The full asset snapshot is stored under `item`."""
        for item_key, item_value in ((evaluation.get("runtime") or {}).get(runtime_key) or {}).items():
            doc = {**base, id_field: item_key, "item": item_value}
            # judgements also carry scenario_id for filtered pagination
            if runtime_key == "judgements" and isinstance(item_value, dict) and item_value.get("scenario_id"):
                doc["scenario_id"] = item_value["scenario_id"]
            # strategies/scenarios also carry their name + tags at the top level
            # (mirrored out of the disabled-index `item` blob) so they can be
            # searched/filtered server-side without reindexing the whole snapshot.
            if runtime_key in ("strategies", "scenarios") and isinstance(item_value, dict):
                if item_value.get("name"):
                    doc["name"] = item_value["name"]
                if item_value.get("tags"):
                    doc["tags"] = item_value["tags"]
            # hyperparameter optimization facts are mirrored out of the blob too
            if runtime_key == "strategies" and isinstance(item_value, dict):
                if item_value.get("_variant_count") is not None:
                    doc["variant_count"] = item_value["_variant_count"]
                if item_value.get("_winner_variant_id"):
                    doc["winner_variant_id"] = item_value["_winner_variant_id"]
            if runtime_key == "scenarios" and isinstance(item_value, dict) and item_value.get("_split"):
                doc["split"] = item_value["_split"]
            actions.append({
                "_op_type": "create",
                "_index": collection_index,
                "_id": utils.unique_id([run_id, runtime_key, item_key]),
                "_source": doc,
            })

    _append_runtime(RUNTIME_INDICES_INDEX_NAME, "index", "indices")
    _append_runtime(RUNTIME_STRATEGIES_INDEX_NAME, "strategy_id", "strategies")
    _append_runtime(RUNTIME_SCENARIOS_INDEX_NAME, "scenario_id", "scenarios")
    _append_runtime(RUNTIME_JUDGEMENTS_INDEX_NAME, "judgement_id", "judgements")

    # One doc per unrated document. _id/_index are stored as doc_id/doc_index so
    # they don't collide with Elasticsearch metadata fields; count/strategies/
    # scenarios stay queryable.
    for u in (evaluation.get("unrated_docs") or []):
        doc = {
            **base,
            "doc_id": u.get("_id"),
            "doc_index": u.get("_index"),
            "count": u.get("count"),
            "strategies": u.get("strategies") or [],
            "scenarios": u.get("scenarios") or [],
            "variants": u.get("variants") or [],
        }
        actions.append({
            "_op_type": "create",
            "_index": UNRATED_DOCS_INDEX_NAME,
            "_id": utils.unique_id([run_id, "unrated", u.get("_index"), u.get("_id")]),
            "_source": doc,
        })

    # One doc per hyperparameter variant: its values, ranking, and aggregated
    # scores per split. Per-search results live in the results stream.
    for v in (evaluation.get("variants") or []):
        actions.append({
            "_op_type": "create",
            "_index": RUNTIME_VARIANTS_INDEX_NAME,
            "_id": utils.unique_id([run_id, "variant", v.get("strategy_id"), v.get("variant_id")]),
            "_source": {**base, **v},
        })

    # One doc per strategy that had failures (per-strategy blob preserved).
    for r in (evaluation.get("results") or []):
        if not r.get("failures"):
            continue
        strategy_id = r.get("strategy_id")
        actions.append({
            "_op_type": "create",
            "_index": FAILURES_INDEX_NAME,
            "_id": utils.unique_id([run_id, "failures", strategy_id]),
            "_source": {**base, "strategy_id": strategy_id, "failures": r.get("failures")},
        })

    # Bulk write; tolerate benign already-exists conflicts from idempotent
    # retries, but surface any real error so the caller does NOT flip the run to
    # a terminal "complete" state over incomplete data.
    _, errors = helpers.bulk(
        client, actions, raise_on_error=False, refresh="wait_for", stats_only=False,
    )
    real_errors = [
        e for e in (errors or [])
        if (e.get("create", e.get("index", {})) or {}).get("status") != 409
    ]
    if real_errors:
        raise RuntimeError(f"Failed to write run results/forensics: {real_errors[:5]}")


def run(
        evaluation: Dict[str, Any],
        store_results: Optional[bool] = False,
        started_by = "unknown",
    ) -> Dict[str, Any]:
    """Execute an evaluation for a benchmark.

    Args:
        evaluation: The evaluation configuration to run. To test one set of
            hyperparameter values, set `task.hyperparameter_values` to values
            by hyperparameter name. They replace the promoted values for this
            run, and needn't be valid testable values. They can't combine with
            `task.optimization` or `store_results`.
        store_results: Whether to store the results in Elasticsearch.
        started_by: The username or system that started the evaluation.

    Returns:
        A dictionary containing the evaluation results and metadata.

    Raises:
        Exception: If the evaluation fails.
    """
    
    # Start timer
    started_at = time.time()
    evaluation["@meta"] = {
        "started_at": utils.timestamp(started_at),
        "started_by": started_by,
    }
    evaluation_id = evaluation.pop("_id", None)
    rank_eval_requests_count = 0

    # Live progress, written incrementally to the run doc as rank_eval batches
    # complete so the UI can render a progress bar while @meta.status ==
    # "running". requests_total is computed once candidates/judgements are
    # resolved (see below); requests_succeeded/requests_failed accumulate as
    # each batch's rank_eval response comes back. These are also folded into
    # the terminal doc (see RunComplete/RunFail/RunSkip below), so the
    # succeeded/failed breakdown remains visible after the run finishes.
    requests_total = 0
    requests_succeeded_count = 0
    requests_failed_count = 0
    _last_progress_write = { "ts": 0.0 }

    def persist_progress(force: bool = False):
        """Best-effort partial update of the run doc's `progress` field.

        Throttled to at most once per second (always flushing when `force` is
        set, e.g. once the total is first known, and on the very last batch)
        so a run with many small batches doesn't hammer the run doc with an
        update per batch. Never raises -- a dropped progress update must not
        fail the run.
        """
        if not store_results or not evaluation_id:
            return
        now = time.time()
        if not force and (now - _last_progress_write["ts"]) < 1.0:
            return
        _last_progress_write["ts"] = now
        try:
            es("studio").update(
                index=INDEX_NAME,
                id=evaluation_id,
                doc={
                    "progress": {
                        "requests_total": requests_total,
                        "requests_completed": requests_succeeded_count + requests_failed_count,
                        "requests_succeeded": requests_succeeded_count,
                        "requests_failed": requests_failed_count,
                    }
                },
            )
        except (ConnectionError, ConnectionTimeout, ApiError):
            logger.exception(
                "Failed to persist run progress",
                extra={"evaluation_id": evaluation_id},
            )

    # Get benchmark settings for batch size and delay
    benchmark_batch_size = RANK_EVAL_BATCH_SIZE
    benchmark_batch_delay_sec = RANK_EVAL_BATCH_DELAY_SEC
    benchmark_id = evaluation.get("benchmark_id")
    if benchmark_id:
        try:
            es_response = es("studio").get(
                index=CONFIGS_INDEX_NAME,
                id=benchmark_id,
                source_includes=["task.rank_eval_batch_size", "task.rank_eval_batch_delay"]
            )
            benchmark_source = es_response.body["_source"]
            if benchmark_source.get("task", {}).get("rank_eval_batch_size"):
                benchmark_batch_size = benchmark_source["task"]["rank_eval_batch_size"]
            if benchmark_source.get("task", {}).get("rank_eval_batch_delay") is not None:
                benchmark_batch_delay_sec = benchmark_source["task"]["rank_eval_batch_delay"] / 1000.0  # Convert ms to seconds
        except Exception:
            # Fallback to env defaults if benchmark fetch fails
            pass

    def persist_benchmark_requests_count(requests_count: int):
        benchmark_id = evaluation.get("benchmark_id")
        if not benchmark_id:
            return
        try:
            es("studio").update(
                index=CONFIGS_INDEX_NAME,
                id=benchmark_id,
                script={
                    "source": """
                        if (ctx._source.task == null) {
                            ctx._source.task = [:];
                        }
                        ctx._source.task.requests = params.requests;
                    """,
                    "lang": "painless",
                    "params": { "requests": requests_count }
                },
                refresh=True
            )
        except (ConnectionError, ConnectionTimeout, ApiError):
            logger.exception(
                "Failed to persist task.requests in benchmark",
                extra={
                    "benchmark_id": benchmark_id,
                    "requests": requests_count,
                    "evaluation_id": evaluation_id
                }
            )

    # Ad hoc hyperparameter values apply to this run only, so they stay out of
    # the task that the run models validate. They go back on the result.
    hyperparameter_values = {}

    def with_hyperparameter_values(result: Dict[str, Any]) -> Dict[str, Any]:
        if hyperparameter_values:
            result["task"]["hyperparameter_values"] = hyperparameter_values
        return result

    try:
    
        # Parse and validate request
        workspace_id = evaluation["workspace_id"]
        hyperparameter_values = evaluation["task"].pop("hyperparameter_values", None) or {}
        
        # Select candidates for strategies and scenarios
        candidates = benchmarks.make_candidate_pool(workspace_id, evaluation["task"])
        
        # If there are no strategies or scenarios that meet the criteria of the
        # benchmark task definition, mark the evaluation as "skipped" and exit.
        if not candidates["strategies"] or not candidates["scenarios"]:
            if store_results:
                doc_updates = {
                    "took": int((time.time() - started_at) * 1000),
                    "progress": {
                        "requests_total": 0,
                        "requests_completed": 0,
                        "requests_succeeded": 0,
                        "requests_failed": 0,
                    },
                }
                doc_updates = RunSkip.model_validate(doc_updates).serialize()
                client = es("studio")
                es_response = client.update(
                    index=INDEX_NAME,
                    id=evaluation_id,
                    doc=doc_updates,
                    refresh=True
                )
                return es_response
        
        # Track the strategies and scenarios that were selected for this evaluation
        evaluation["strategy_id"] = sorted([ c["_id"] for c in candidates["strategies"] ])
        evaluation["scenario_id"] = sorted([ c["_id"] for c in candidates["scenarios"] ])
        
        # Prepare _rank_eval request
        _rank_eval = {
            "templates": [],
            "requests": [],
            "metric": {}
        }
        
        # Store the contents of the assets used at runtime in this evaluation
        evaluation["runtime"] = {
            "indices": {},
            "strategies": {},
            "scenarios": {},
            "judgements": {}
        }
        
        # Set a default size of 10,000 hits per request when retrieving
        # strategies, scenarios, or judgements
        size = 10000
        
        # Get the index pattern and rating scale of workspace
        client = es("studio")
        es_response = client.get(
            index="esrs-workspaces",
            id=workspace_id,
            source_includes=["index_pattern","rating_scale"]
        )
        index_pattern = es_response.body["_source"]["index_pattern"]
        # TODO: rating_scale_max will be used when implementing the err metric
        rating_scale_max = es_response.body["_source"]["rating_scale"]["max"]
        
        # Get the strategies, add them to "templates" in _rank_eval,
        # and track their runtime contents.
        hits = []
        
        # Don't fetch strategies that were given as docs 
        strategies_to_fetch = []
        for candidate in candidates["strategies"]:
            if candidate.get("_source"):
                hits.append({
                    "_id": candidate["_id"],
                    "_source": candidate["_source"]
                })
            else:
                strategies_to_fetch.append(candidate["_id"])
                
        # Fetch strategies for given candidates
        if strategies_to_fetch:
            body = {
                "query": { "ids": { "values": strategies_to_fetch }},
                "size": size,
                "version": True,
                "_source": { "excludes": [ "_search" ]},
            }
            es_response = client.search(
                index="esrs-strategies",
                body=body
            )
            for hit in es_response.body["hits"]["hits"]:
                hits.append({
                    "_id": hit["_id"],
                    "_source": hit["_source"]
                })

        # Resolve the hyperparameter optimization settings. Without them, every
        # strategy is the degenerate case of a single baseline variant.
        optimization_task = Optimization.model_validate(
            evaluation["task"].get("optimization") or {}
        ).model_dump()
        has_optimization = bool(evaluation["task"].get("optimization"))
        task_metrics = evaluation["task"]["metrics"]
        objective = optimization_task["objective"]
        if not has_optimization and objective["metric"] not in task_metrics:
            objective = { **objective, "metric": task_metrics[0] }
        if objective["metric"] not in task_metrics:
            raise ValueError("optimization.objective.metric must be one of the task metrics")
        latency_constraint = optimization_task.get("latency_constraint")
        holdout_ratio = optimization_task["holdout"]["ratio"]
        default_seed = evaluation.get("benchmark_id") or "default"
        search_seed = optimization_task.get("seed") or default_seed
        holdout_seed = optimization_task["holdout"].get("seed") or search_seed
        top_n = optimization_task["store_hits_top_n"]
        if has_optimization:
            # Record the resolved seeds so the run is reproducible.
            evaluation["task"]["optimization"]["seed"] = search_seed
            evaluation["task"]["optimization"].setdefault("holdout", {})["seed"] = holdout_seed

        # Ad hoc hyperparameter values replace the promoted values of a test run.
        # They aren't stored, so a stored run can't use them. They also need a
        # single variant per strategy, so they can't combine with optimization.
        if hyperparameter_values:
            if not isinstance(hyperparameter_values, dict):
                raise ValueError("task.hyperparameter_values must be an object of values by hyperparameter name")
            if store_results:
                raise ValueError("task.hyperparameter_values can't be used when storing results")
            if has_optimization:
                raise ValueError("task.hyperparameter_values can't be used with task.optimization")
            defined = { h["name"] for hit in hits for h in (hit["_source"].get("hyperparameters") or []) }
            unknown = sorted(set(hyperparameter_values) - defined)
            if unknown:
                raise ValueError(f"task.hyperparameter_values has undefined hyperparameters: {', '.join(unknown)}")

        # Each strategy has a plan: its resolved hyperparameters and variants
        plans = {}
        templates_by_id = {}
        for hit in sorted(hits, key=lambda h: h["_id"]):
            strategy_id = hit["_id"]
            if "~" in strategy_id:
                raise ValueError(f"strategy _id '{strategy_id}' must not contain '~'")
            template = hit["_source"]["template"]["source"]
            template_entry = {
                "id": strategy_id,
                "template": {
                    "source": template
                }
            }
            _rank_eval["templates"].append(template_entry)
            templates_by_id[strategy_id] = template_entry
            fingerprint = utils.fingerprint([ template ])
            hyperparameters = hit["_source"].get("hyperparameters") or []
            undefined = [
                n for n in utils.extract_hyperparameter_refs(template)
                if n not in { h["name"] for h in hyperparameters }
            ]
            if undefined:
                raise ValueError(
                    f"strategy '{strategy_id}' references undefined hyperparameters: {', '.join(undefined)}"
                )
            resolved_space = optimization.resolve_hyperparameters(
                hyperparameters, optimization_task["values_to_test"], strategy_id,
                optimization_task["points_per_range"], optimize=has_optimization,
                overrides=hyperparameter_values,
            )
            variants = optimization.generate_variants(
                resolved_space,
                fingerprint,
                optimization_task["algorithm"],
                optimization_task["sample_size"],
                search_seed,
            )
            plans[strategy_id] = {
                "fingerprint": fingerprint,
                "hyperparameters": resolved_space,
                "variants": variants,
                "baseline_variant_id": next(v["variant_id"] for v in variants if v["is_baseline"]),
            }
            runtime_strategy = {
                "_fingerprint": fingerprint,
                "_resolved_hyperparameters": resolved_space,
                "_algorithm": optimization_task["algorithm"],
                "_variant_count": len(variants),
            }
            for field, value in hit["_source"].items():
                if field == "workspace_id":
                    continue
                runtime_strategy[field] = value
            evaluation["runtime"]["strategies"][strategy_id] = runtime_strategy
        
        # Get judgements, add them to "ratings" in _rank_eval, and track their
        # original contents. Track which scenarios had judgements, in case the
        # request includes scenarios that have no judgements.
        # 
        # TODO: Implement random sampling for judgements, because there could be
        # more than 10,000 judgements per scenario.
        body = {
            "query": { "terms": { "scenario_id": evaluation["scenario_id"] }},
            "size": size,
            "version": True,
            "_source": { "excludes": [ "_search" ]},
        }
        es_response = client.search(
            index="esrs-judgements",
            body=body
        )
        ratings = {}
        for hit in es_response.body["hits"]["hits"]:
            scenario_id = hit["_source"]["scenario_id"]
            if scenario_id not in ratings:
                ratings[scenario_id] = []
            ratings[scenario_id].append({
                "_index": hit["_source"]["index"],
                "_id": hit["_source"]["doc_id"],
                "rating": hit["_source"]["rating"],
            })
            runtime_judgement = {
                "_fingerprint": utils.fingerprint([ hit["_id"], hit["_source"]["rating"] ])
            }
            for field, value in hit["_source"].items():
                if field == "workspace_id":
                    continue
                runtime_judgement[field] = value
            evaluation["runtime"]["judgements"][hit["_id"]] = runtime_judgement
        
        # Get scenarios
        scenarios = {}
        body = {
            "query": { "ids": { "values": evaluation["scenario_id"] }},
            "size": size,
            "version": True,
            "_source": { "excludes": [ "_search" ]},
        }
        es_response = client.search(
            index="esrs-scenarios",
            body=body
        )
        for hit in es_response.body["hits"]["hits"]:
            scenarios[hit["_id"]] = hit["_source"]["values"]
            runtime_scenario = {
                "_fingerprint": utils.fingerprint([ hit["_source"]["values"] ])
            }
            for field, value in hit["_source"].items():
                if field == "workspace_id":
                    continue
                runtime_scenario[field] = value
            evaluation["runtime"]["scenarios"][hit["_id"]] = runtime_scenario
            
        # Store index relevance fingerprints (optional in serverless mode)
        try:
            evaluation["runtime"]["indices"] = content.make_index_relevance_fingerprints(index_pattern)
        except Exception:
            # Fallback for serverless mode where indices.stats API is not available
            evaluation["runtime"]["indices"] = {}
        
        # Configure the metrics for _rank_eval
        metrics_config = {
            # TODO: Support other types of metrics (commented out below)
            #"dcg": {
            #    "name": "dcg",
            #    "config": {
            #        "k":  evaluation["task"]["k"]
            #    }
            #},
            #"err": {
            #    "name": "expected_reciprocal_rank",
            #    "config": {
            #        "k":  evaluation["task"]["k"],
            #        "maximum_relevance": rating_scale_max
            #    }
            #},
            "mrr": {
                "name": "mean_reciprocal_rank",
                "config": {
                    "k":  evaluation["task"]["k"],
                    "relevant_rating_threshold": 1 # TODO: Make configurable
                }
            },
            "ndcg": {
                "name": "dcg",
                "config": {
                    "k": evaluation["task"]["k"],
                    "normalize": True
                }
            },
            "precision": {
                "name": "precision",
                "config": {
                    "k": evaluation["task"]["k"],
                    "ignore_unlabeled": False
                }
            },
            "recall": {
                "name": "recall",
                "config": {
                    "k": evaluation["task"]["k"]
                }
            }
        }
        
        # Store any unrated docs found in the evaluation
        _unrated_docs = {}
        
        # Check if we have any scenarios with ratings
        scenarios_with_ratings = [scenario_id for scenario_id in evaluation["scenario_id"] if scenario_id in ratings and ratings[scenario_id]]

        # Split the scenarios into a tuning set (used to choose between
        # variants) and a holdout set (used only to validate the winner and the
        # baseline variant). Without a holdout, every scenario is a tuning
        # scenario and scores are in-sample.
        tuning_scenarios, holdout_scenarios = optimization.split_scenarios(
            scenarios_with_ratings, holdout_ratio, holdout_seed,
        )
        for scenario_id in tuning_scenarios:
            evaluation["runtime"]["scenarios"][scenario_id]["_split"] = "tuning"
        for scenario_id in holdout_scenarios:
            evaluation["runtime"]["scenarios"][scenario_id]["_split"] = "holdout"

        # The total number of searches this run will submit is known the moment
        # candidates/judgements are resolved: variants x scenarios x metrics for
        # the tuning phase, plus the winning and baseline variants for the
        # holdout phase (an upper bound until winners are known). Persist it
        # immediately (forced, bypassing the throttle) so the UI can render a
        # "0 / total" progress bar as soon as the run starts processing, even
        # before the first batch completes.
        variant_counts = [ len(plans[strategy_id]["variants"]) for strategy_id in sorted(plans) ]
        planned = optimization.estimate_searches(
            variant_counts, len(tuning_scenarios), len(holdout_scenarios), len(task_metrics),
        )
        if scenarios_with_ratings:
            limits = optimization.check_limits(variant_counts, planned["total"])
            if limits["errors"]:
                raise ValueError(" ".join(limits["errors"]))
        requests_total = planned["total"]
        evaluation["progress"] = {
            "requests_total": requests_total,
            "requests_completed": 0,
            "requests_succeeded": 0,
            "requests_failed": 0,
        }
        persist_progress(force=True)

        if not scenarios_with_ratings:
            # If no scenarios have ratings, mark evaluation as skipped
            evaluation["took"] = int((time.time() - started_at) * 1000)
            if store_results:
                # Skipped: no scored results and no runtime snapshot to persist;
                # write only the run doc's terminal status. Strip any heavy
                # fields so they never land on the small run doc.
                skip_doc = RunSkip.model_validate(evaluation).serialize()
                for heavy in ("results", "runtime", "unrated_docs", "variants"):
                    skip_doc.pop(heavy, None)
                client.update(
                    index=INDEX_NAME,
                    id=evaluation_id,
                    doc=skip_doc,
                    refresh=True
                )
            return with_hyperparameter_values(evaluation)

        # Track searches and failures by strategy. A search is one variant
        # against one scenario in one split. Failures are stored at the
        # strategy level because not all errors can be linked to a specific
        # scenario.
        all_searches = { strategy_id: {} for strategy_id in plans }
        all_failures = { strategy_id: [] for strategy_id in plans }

        def run_phase(strategy_id, variant_ids, scenario_ids, split):
            """Run _rank_eval for the given variants of a strategy against the
            given scenarios, once per metric (the API accepts one metric per
            request), and accumulate the results."""
            nonlocal rank_eval_requests_count, requests_succeeded_count, requests_failed_count
            plan = plans[strategy_id]
            values_by_variant = { v["variant_id"]: v["values"] for v in plan["variants"] }
            store = all_searches[strategy_id]
            for m in task_metrics:
                metric = { metrics_config[m]["name"]: metrics_config[m]["config"] }

                # Define a request for each combination of variants and scenarios
                requests = []
                for variant_id in variant_ids:
                    for scenario_id in scenario_ids:
                        key = (variant_id, split, scenario_id)
                        if key not in store:
                            store[key] = {
                                "scenario_id": scenario_id,
                                "variant_id": variant_id,
                                "split": split,
                                "metrics": {},
                                "hits": [],
                                "took": None,
                                "coverage": None,
                                "seen": False,
                            }
                        params = dict(scenarios[scenario_id])
                        if plan["hyperparameters"]:
                            params["hp"] = values_by_variant[variant_id]
                        requests.append({
                            "id": f"{strategy_id}~{variant_id}~{scenario_id}",
                            "template_id": strategy_id,
                            "params": params,
                            "ratings": ratings[scenario_id],
                        })
                if not requests:
                    continue

                def submit(batch_requests):
                    """Submit one _rank_eval request and accumulate its results.

                    Elasticsearch rejects a whole _rank_eval call when any of
                    its rendered templates is invalid (for example, a
                    hyperparameter value that the query doesn't accept). So when
                    a call with several variants fails with a 400, split it by
                    variant and retry each half. The invalid variant then fails
                    alone and the valid variants still get scores."""
                    nonlocal rank_eval_requests_count, requests_succeeded_count, requests_failed_count
                    body = {
                        "metric": metric,
                        "requests": batch_requests,
                        "templates": [ templates_by_id[strategy_id] ],
                    }
                    if optimization_task.get("max_concurrent_searches"):
                        body["max_concurrent_searches"] = optimization_task["max_concurrent_searches"]
                    es_response = None
                    try:
                        es_response = es("content").rank_eval(
                            index=index_pattern,
                            body=body
                        )
                    except (ConnectionError, ConnectionTimeout, ApiError) as e:
                        variants_in_batch = list(dict.fromkeys(
                            r["id"].split("~", 2)[1] for r in batch_requests
                        ))
                        if getattr(e, "status_code", None) == 400 and len(variants_in_batch) > 1:
                            half = set(variants_in_batch[:len(variants_in_batch) // 2])
                            submit([ r for r in batch_requests if r["id"].split("~", 2)[1] in half ])
                            submit([ r for r in batch_requests if r["id"].split("~", 2)[1] not in half ])
                            return
                        rank_eval_requests_count += len(batch_requests)
                        failure = {
                            "scenario_id": None,
                            "metric": m,
                            "error": {
                                "type": e.__class__.__name__,
                                "reason": str(e)
                            }
                        }
                        if len(variants_in_batch) == 1:
                            failure["variant_id"] = variants_in_batch[0]
                        all_failures[strategy_id].append(failure)
                        # The whole batch failed to submit, so every request in
                        # it counts as failed for progress purposes.
                        requests_failed_count += len(batch_requests)
                        persist_progress()
                        return
                    rank_eval_requests_count += len(batch_requests)

                    # Store results
                    for request_id, details in es_response.body["details"].items():
                        _, variant_id, scenario_id = request_id.split("~", 2)
                        entry = store[(variant_id, split, scenario_id)]
                        entry["metrics"][m] = details["metric_score"]
                        if not entry["seen"]:
                            entry["seen"] = True
                            entry["hits"] = details["hits"]
                            entry["coverage"] = optimization.coverage(details["hits"])
                            # "took" (ms to run this search) is only present in
                            # Elasticsearch 9.6.0+ rank_eval responses; omit it
                            # entirely against older clusters rather than storing
                            # a misleading 0/null.
                            entry["took"] = details.get("took")
                            # Find unrated docs
                            for hit in details["hits"]:
                                if hit["rating"] is not None:
                                    continue
                                _index = hit["hit"]["_index"]
                                _id = hit["hit"]["_id"]
                                if _index not in _unrated_docs:
                                    _unrated_docs[_index] = {}
                                if _id not in _unrated_docs[_index]:
                                    _unrated_docs[_index][_id] = {
                                        "count": 0,
                                        "strategies": set(),
                                        "scenarios": set(),
                                        "variants": set(),
                                    }
                                _unrated_docs[_index][_id]["count"] += 1
                                _unrated_docs[_index][_id]["strategies"].add(strategy_id)
                                _unrated_docs[_index][_id]["scenarios"].add(scenario_id)
                                _unrated_docs[_index][_id]["variants"].add(variant_id)

                    # Store failures
                    batch_failures = es_response.body.get("failures") or {}
                    if batch_failures:
                        for request_id, failure in batch_failures.items():
                            _, variant_id, scenario_id = request_id.split("~", 2)
                            all_failures[strategy_id].append({
                                "scenario_id": scenario_id,
                                "variant_id": variant_id,
                                "metric": m,
                                "error": failure.get("error") or failure
                            })

                    # Update progress: every request in the batch is now
                    # accounted for as either succeeded (has a `details` entry)
                    # or failed (has a `failures` entry).
                    requests_succeeded_count += len(es_response.body.get("details") or {})
                    requests_failed_count += len(batch_failures)
                    persist_progress()

                # Batch the requests to avoid overwhelming Elasticsearch
                for batch_index, batch_requests in enumerate(utils.chunks(requests, benchmark_batch_size)):

                    # Throttle between batches
                    if batch_index > 0 and benchmark_batch_delay_sec > 0:
                        time.sleep(benchmark_batch_delay_sec)
                    submit(batch_requests)

        def aggregates_for(strategy_id, variant_id, split):
            return optimization.aggregate_searches([
                entry for (vid, sp, _), entry in all_searches[strategy_id].items()
                if vid == variant_id and sp == split
            ])

        # Run one strategy at a time, so each strategy's variants are ranked on
        # the tuning set before anything touches the holdout set.
        outcomes = {}
        variant_docs = []
        for strategy_id in sorted(plans):
            plan = plans[strategy_id]
            variants = plan["variants"]
            baseline_id = plan["baseline_variant_id"]

            # Tuning phase: every variant against the tuning scenarios
            run_phase(strategy_id, [ v["variant_id"] for v in variants ], tuning_scenarios, "tuning")
            tuning_aggregates = {
                v["variant_id"]: aggregates_for(strategy_id, v["variant_id"], "tuning") for v in variants
            }
            ranked = optimization.rank_variants(
                [{ "variant_id": vid, "aggregates": agg } for vid, agg in tuning_aggregates.items()],
                objective,
                latency_constraint,
            )
            winner = next((v for v in ranked if v["is_winner"]), None)
            winner_id = winner["variant_id"] if winner else baseline_id

            # Holdout phase: only the winning and baseline variants. The holdout
            # set never informs the choice of winner.
            holdout_ids = []
            holdout_aggregates = {}
            if holdout_scenarios:
                holdout_ids = list(dict.fromkeys([ winner_id, baseline_id ]))
                run_phase(strategy_id, holdout_ids, holdout_scenarios, "holdout")
                holdout_aggregates = {
                    vid: aggregates_for(strategy_id, vid, "holdout") for vid in holdout_ids
                }
                if len(holdout_ids) < 2 and len(variants) > 1:
                    # The winner is the baseline, so the planned second variant
                    # won't run.
                    requests_total -= len(holdout_scenarios) * len(task_metrics)
                    persist_progress(force=True)

            # Store hits only for the top variants, the winner, and the baseline
            keep = { v["variant_id"] for v in ranked[:top_n] } | { winner_id, baseline_id }
            for (vid, _, _), entry in all_searches[strategy_id].items():
                if vid not in keep:
                    entry["hits"] = []
            for v in ranked:
                variant = next(x for x in variants if x["variant_id"] == v["variant_id"])
                variant_docs.append({
                    "strategy_id": strategy_id,
                    "variant_id": v["variant_id"],
                    "is_baseline": variant["is_baseline"],
                    "is_winner": v["variant_id"] == winner_id,
                    "values": variant["values"],
                    "hits_stored": v["variant_id"] in keep,
                    "score": v["score"],
                    "rank": v["rank"],
                    "violates_constraint": v["violates_constraint"],
                    "aggregates": {
                        "tuning": tuning_aggregates[v["variant_id"]],
                        "holdout": holdout_aggregates.get(v["variant_id"]),
                    },
                })
            outcomes[strategy_id] = {
                "winner_id": winner_id,
                "baseline_id": baseline_id,
                "no_valid_winner": winner is None,
            }
            runtime_strategy = evaluation["runtime"]["strategies"][strategy_id]
            runtime_strategy["_winner_variant_id"] = winner_id

        # Restructure results for response
        evaluation["results"] = []
        split_order = { "tuning": 0, "holdout": 1 }
        for strategy_id in evaluation["strategy_id"]:
            variant_order = { v["variant_id"]: i for i, v in enumerate(plans[strategy_id]["variants"]) }
            entries = sorted(
                all_searches[strategy_id].values(),
                key=lambda e: (variant_order[e["variant_id"]], split_order[e["split"]], e["scenario_id"]),
            )
            searches = []
            for entry in entries:
                search = { k: v for k, v in entry.items() if k not in ("seen", "took", "coverage") }
                if entry.get("took") is not None:
                    search["took"] = entry["took"]
                if entry.get("coverage") is not None:
                    search["coverage"] = entry["coverage"]
                searches.append(search)
            evaluation["results"].append({
                "strategy_id": strategy_id,
                "searches": searches,
                "failures": all_failures[strategy_id],
            })
        evaluation["variants"] = variant_docs

        # Restructure unrated_docs for response
        unrated_docs = []
        for _index in sorted(_unrated_docs.keys()):
            for _id in sorted(_unrated_docs[_index].keys()):
                doc = _unrated_docs[_index][_id]
                unrated_docs.append({
                    "_index": _index,
                    "_id": _id,
                    "count": doc["count"],
                    "strategies": sorted(list(doc["strategies"])),
                    "scenarios": sorted(list(doc["scenarios"])),
                    "variants": sorted(list(doc["variants"])),
                })
        evaluation["unrated_docs"] = sorted(unrated_docs, key=lambda doc: doc["count"], reverse=True)

        # Summarize metrics of each strategy's winning variant. The headline
        # score (`_total`) is the holdout score when there is a holdout, and an
        # in-sample score otherwise.
        evaluation["summary"] = _generate_optimization_summary(
            evaluation,
            candidates["strategies"],
            candidates["scenarios"],
            plans,
            outcomes,
            has_holdout=bool(holdout_scenarios),
        )
        evaluation["task"]["requests"] = rank_eval_requests_count

        # Finalize progress: requests_completed should equal requests_total
        # (every planned request was attempted), preserved on the terminal doc
        # so the succeeded/failed breakdown remains visible after the run ends.
        evaluation["progress"] = {
            "requests_total": requests_total,
            "requests_completed": requests_succeeded_count + requests_failed_count,
            "requests_succeeded": requests_succeeded_count,
            "requests_failed": requests_failed_count,
        }
        
        # Create final response
        stopped_at = time.time()
        evaluation["took"] = int(( stopped_at - started_at) * 1000)
        doc = with_hyperparameter_values(RunComplete.model_validate(evaluation).serialize())

        # Store results
        if store_results:
            # Write results + forensics into the data streams BEFORE flipping the
            # run doc's terminal status, so the run doc's status is the single
            # source of truth for "this run's data is complete and trustworthy."
            _write_results_and_forensics(doc, evaluation_id)

            # The run doc itself stays small: strip the heavy fields that now live
            # in the data streams before writing it.
            run_doc = {k: v for k, v in doc.items() if k not in ("results", "runtime", "unrated_docs", "variants")}
            es_response = client.update(
                index=INDEX_NAME,
                id=evaluation_id,
                doc=run_doc,
                refresh=True
            )
            persist_benchmark_requests_count(rank_eval_requests_count)
        return doc
    
    # Mark evaluation as "failed" on exception
    except Exception as e:
        logger.exception(e)
        stopped_at = time.time()
        evaluation["took"] = int(( stopped_at - started_at) * 1000)
        evaluation["error"] = {
            "type": e.__class__.__name__,
            "message": str(e),
            "traceback": "".join(traceback.format_exception(type(e), e, e.__traceback__))
        }
        evaluation["task"]["requests"] = rank_eval_requests_count
        # Preserve whatever progress had accumulated before the failure (may be
        # all zeros if the exception happened before requests_total was known).
        evaluation["progress"] = {
            "requests_total": requests_total,
            "requests_completed": requests_succeeded_count + requests_failed_count,
            "requests_succeeded": requests_succeeded_count,
            "requests_failed": requests_failed_count,
        }
        doc = with_hyperparameter_values(RunFail.model_validate(evaluation).serialize())
        if store_results:
            client = es("studio")
            # Persist whatever results/forensics were accumulated before the
            # failure (best-effort) before flipping the terminal status, same
            # ordering guarantee as the completed path. A secondary failure here
            # must not mask the original error, so it is swallowed and logged.
            try:
                _write_results_and_forensics(doc, evaluation_id)
            except Exception:
                logger.exception(
                    "Failed to persist results/forensics for failed run",
                    extra={"run_id": evaluation_id},
                )
            run_doc = {k: v for k, v in doc.items() if k not in ("results", "runtime", "unrated_docs", "variants")}
            client.update(
                index=INDEX_NAME,
                id=evaluation_id,
                doc=run_doc,
                refresh=True
            )
            persist_benchmark_requests_count(rank_eval_requests_count)
        raise e
    
def search(
        workspace_id: str,
        benchmark_id: str,
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """Search for evaluations.

    Each hit is the small run document (status, task, summary, error, took,
    progress) -- see get() for details on the `progress` field, which is
    updated live while a run is "running" and preserved after it finishes.

    Args:
        workspace_id: The UUID of the workspace.
        benchmark_id: The UUID of the benchmark.
        text: Search text for filtering evaluations.
        filters: List of additional Elasticsearch filters.
        sort: Sorting configuration for the search.
        size: Number of evaluations to return per page.
        page: Page number for pagination.
        aggs: Whether to include aggregations.

    Returns:
        A dictionary containing the search results.
    """
    filters = [{ "term": { "benchmark_id": benchmark_id }}]
    response = utils.search_assets(
        "runs", workspace_id, text, filters, sort, size, page,
    )
    return response

def get(_id: str) -> Dict[str, Any]:
    """Get a run by its _id.

    Returns the small run document (status, task, summary, error, took,
    progress). The heavy per-search results and the runtime/unrated-docs audit
    trail are NOT on this document; fetch them via the paginated
    get_results/get_runtime_*/get_unrated_docs/get_failures endpoints, or get
    everything in one call via get_full.

    While @meta.status == "running", `progress` (requests_total,
    requests_completed, requests_succeeded, requests_failed) is updated
    incrementally by the worker as rank_eval batches complete, so polling this
    endpoint (or search()) is enough to render a live progress bar. It's also
    preserved on terminal docs, so a "completed" run can still show a nonzero
    requests_failed (individual rank_eval errors don't abort the run -- only an
    unhandled exception marks a run "failed").

    Args:
        _id: The UUID of the run.

    Returns:
        The run document from Elasticsearch.
    """
    client = es("studio")
    es_response = client.get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

####  Run forensics (per-item data streams, paginated)  ########################
#
# A run's forensics are fanned out into dedicated per-item data streams so each
# collection can be fetched independently and paginated server-side. The UI/MCP
# should fetch only the collection(s) a given view needs:
#   * Summary/heatmap labels -> get_runtime_strategies (whole; bounded by #strategies)
#   * Runtime flyout tabs     -> get_runtime_{indices,scenarios,judgements} (paginated)
#   * Unrated-docs panel      -> get_unrated_docs (paginated)
#   * Debug                   -> get_failures
#   * Per-search metrics/took -> get_results (paginated)
#   * Full-run export         -> get_full (NOT paginated; assembles everything server-side)

MAX_RUNTIME_STRATEGIES = 10000  # strategies are bounded by the run's task; fetched whole


def _paginate_run_collection(
        index: str,
        run_id: str,
        size: int = 25,
        page: int = 1,
        extra_filters: Optional[List[Dict[str, Any]]] = None,
        sort: Optional[List[Any]] = None,
        text: str = "",
    ) -> Dict[str, Any]:
    """Page over a per-run forensics data stream, filtered by run_id.

    `text`, if given, free-text matches against the (mirrored, top-level)
    `name` field — the only part of a strategy/scenario snapshot that's
    actually indexed, since the full `item` blob is stored with indexing
    disabled to avoid cross-run mapping conflicts.

    Returns {"run_id", "total", "size", "page", "items": [_source, ...]}.
    Empty (total 0) if the stream doesn't exist yet (e.g. a skipped run).
    """
    client = es("studio")
    filters = [{"term": {"run_id": run_id}}]
    if extra_filters:
        filters.extend(extra_filters)
    body = {
        "query": {"bool": {"filter": filters}},
        "size": max(0, size),
        "from": max(0, (page - 1) * size),
        "track_total_hits": True,
    }
    if text:
        body["query"]["bool"]["must"] = [{
            "query_string": {"query": text, "default_operator": "AND", "fields": ["name"]}
        }]
    if sort:
        body["sort"] = sort
    try:
        es_response = client.search(index=index, body=body)
    except NotFoundError:
        return {"run_id": run_id, "total": 0, "size": size, "page": page, "items": []}
    hits = es_response.body.get("hits", {})
    total = hits.get("total", {}).get("value", 0) if isinstance(hits.get("total"), dict) else hits.get("total", 0)
    items = [h["_source"] for h in hits.get("hits", [])]
    return {"run_id": run_id, "total": total, "size": size, "page": page, "items": items}


def _tags_for_run_collection(index: str, run_id: str) -> List[str]:
    """Distinct `tags` values across a run's items in a runtime collection.

    Backs the Tags filter dropdowns in the runtime-assets flyout. Empty
    (rather than erroring) if the stream doesn't exist yet.
    """
    client = es("studio")
    body = {
        "query": {"bool": {"filter": [{"term": {"run_id": run_id}}]}},
        "size": 0,
        "aggs": {"tags": {"terms": {"field": "tags", "size": 10000, "order": {"_key": "asc"}}}},
    }
    try:
        es_response = client.search(index=index, body=body)
    except NotFoundError:
        return []
    buckets = es_response.body.get("aggregations", {}).get("tags", {}).get("buckets", [])
    return [bucket["key"] for bucket in buckets]


def get_runtime_strategies(run_id: str, tags: Optional[List[str]] = None, text: str = "") -> Dict[str, Any]:
    """Get ALL runtime strategy snapshots for a run (not paginated).

    Strategies are bounded by the run's task definition, so the Summary table and
    heatmap fetch the whole set to label rows/axes.

    Optionally filter by `tags` (OR-matched against each strategy's tags) and/or
    `text` (free-text matched against each strategy's name), which the
    runtime-assets flyout uses to filter server-side.

    Returns {"run_id", "total", "items": [{strategy_id, item, ...}, ...]}.
    """
    extra = [{"terms": {"tags": tags}}] if tags else None
    result = _paginate_run_collection(
        RUNTIME_STRATEGIES_INDEX_NAME, run_id, size=MAX_RUNTIME_STRATEGIES, page=1, extra_filters=extra, text=text,
    )
    return {"run_id": run_id, "total": result["total"], "items": result["items"]}


def get_runtime_strategies_tags(run_id: str) -> Dict[str, Any]:
    """List the distinct tags across a run's runtime strategy snapshots."""
    return {"run_id": run_id, "tags": _tags_for_run_collection(RUNTIME_STRATEGIES_INDEX_NAME, run_id)}


def get_runtime_indices(run_id: str, size: int = 25, page: int = 1) -> Dict[str, Any]:
    """Get a page of runtime index snapshots for a run."""
    return _paginate_run_collection(RUNTIME_INDICES_INDEX_NAME, run_id, size, page)


def get_runtime_scenarios(
        run_id: str, size: int = 25, page: int = 1, tags: Optional[List[str]] = None, text: str = "",
    ) -> Dict[str, Any]:
    """Get a page of runtime scenario snapshots for a run.

    Optionally filter by `tags` (OR-matched against each scenario's tags) and/or
    `text` (free-text matched against each scenario's name), which the
    runtime-assets flyout uses to filter server-side.
    """
    extra = [{"terms": {"tags": tags}}] if tags else None
    return _paginate_run_collection(RUNTIME_SCENARIOS_INDEX_NAME, run_id, size, page, extra_filters=extra, text=text)


def get_runtime_scenarios_tags(run_id: str) -> Dict[str, Any]:
    """List the distinct tags across a run's runtime scenario snapshots."""
    return {"run_id": run_id, "tags": _tags_for_run_collection(RUNTIME_SCENARIOS_INDEX_NAME, run_id)}


def get_runtime_judgements(run_id: str, size: int = 25, page: int = 1, scenario_id: str = "") -> Dict[str, Any]:
    """Get a page of runtime judgement snapshots for a run.

    Optionally filter by `scenario_id` (every judgement doc carries one), which
    makes the judgement-gap-fill workflow cheap even for very large runs.
    """
    extra = [{"term": {"scenario_id": scenario_id}}] if scenario_id else None
    return _paginate_run_collection(RUNTIME_JUDGEMENTS_INDEX_NAME, run_id, size, page, extra_filters=extra)


def get_unrated_docs(
        run_id: str,
        size: int = 25,
        page: int = 1,
        winners_only: bool = False,
    ) -> Dict[str, Any]:
    """Get a page of a run's unrated documents, most-unrated first.

    Items are the stored shape {doc_id, doc_index, count, strategies, scenarios,
    variants}. `variants` lists the variant IDs whose searches returned the
    document.

    A hyperparameter search surfaces many documents that only losing variants
    return. With `winners_only`, keep the documents that the winning variant of
    a strategy returned (or the baseline variant, for a strategy without
    hyperparameters). Those are the documents worth judging first. `count`
    still counts every search that returned the document.
    """
    extra_filters = None
    if winners_only:
        winners = _fetch_all_run_collection(
            RUNTIME_VARIANTS_INDEX_NAME, run_id,
            extra_filters=[{ "term": { "is_winner": True }}],
        )
        extra_filters = [{ "terms": { "variants": sorted({ w["variant_id"] for w in winners }) }}]
    return _paginate_run_collection(
        UNRATED_DOCS_INDEX_NAME, run_id, size, page,
        sort=[{"count": "desc"}],
        extra_filters=extra_filters,
    )


def get_failures(run_id: str, size: int = 25, page: int = 1) -> Dict[str, Any]:
    """Get a page of a run's per-strategy failures."""
    return _paginate_run_collection(FAILURES_INDEX_NAME, run_id, size, page)


def get_results(
        run_id: str,
        size: int = 25,
        page: int = 1,
        strategy_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        split: Optional[str] = None,
    ) -> Dict[str, Any]:
    """Get a page of a run's scored (strategy x variant x scenario) results.

    Items are the stored shape {run_id, workspace_id, benchmark_id, strategy_id,
    variant_id, split, scenario_id, metrics, hits, took (if the cluster reported
    it), coverage, @timestamp}. This is the only way to retrieve the heavy
    per-search results (and `took`) for a run -- they're deliberately excluded
    from the run doc itself. Hits are stored only for the winner, the baseline,
    and the top variants (`variants[].hits_stored`).

    Pass `strategy_id`, `variant_id` and/or `split` (`tuning` or `holdout`) to
    narrow the results, for example to read every scenario score of one variant.
    """
    extra_filters = []
    if strategy_id:
        extra_filters.append({ "term": { "strategy_id": strategy_id }})
    if variant_id:
        extra_filters.append({ "term": { "variant_id": variant_id }})
    if split:
        extra_filters.append({ "term": { "split": split }})
    return _paginate_run_collection(
        RESULTS_INDEX_NAME, run_id, size, page,
        sort=[{"strategy_id": "asc"}, {"variant_id": "asc"}, {"scenario_id": "asc"}],
        extra_filters=extra_filters or None,
    )


def _fetch_all_run_collection(index: str, run_id: str, **kwargs) -> List[Dict[str, Any]]:
    """Fetch every item in a per-run data stream, not just one page.

    Pages internally against Elasticsearch (so no single request there is
    unbounded either), but the caller gets back one complete list -- no
    pagination is exposed to callers of `get_full` below.
    """
    items: List[Dict[str, Any]] = []
    page = 1
    size = 1000
    while True:
        result = _paginate_run_collection(index, run_id, size=size, page=page, **kwargs)
        items.extend(result["items"])
        if not result["items"] or len(items) >= result["total"]:
            break
        page += 1
    return items


def get_full(run_id: str) -> Dict[str, Any]:
    """Get EVERYTHING about a run, assembled server-side in a single call.

    Unlike `get` (the slim run doc) or the paginated get_results/get_runtime_*/
    get_unrated_docs/get_failures endpoints above (meant for incremental/UI
    consumption), this fetches every item from every per-run collection --
    not paginated from the caller's perspective -- and merges them onto the
    run doc. This is what backs the "Download run" UI action and the
    equivalent REST/MCP endpoints, so a comprehensive export is available in
    one round trip instead of requiring N client-orchestrated paginated calls.

    Returns the run doc's fields plus:
      - results: every (strategy, scenario) scored result (metrics, hits, took)
      - runtime: {strategies, indices, scenarios, judgements}, each a full list
      - unrated_docs: every unrated doc
      - failures: every per-strategy failure doc
    """
    client = es("studio")
    es_response = client.get(index=INDEX_NAME, id=run_id, source_excludes="_search")
    run = dict(es_response["_source"])
    run["_id"] = es_response["_id"]
    run["results"] = _fetch_all_run_collection(
        RESULTS_INDEX_NAME, run_id, sort=[{"strategy_id": "asc"}, {"scenario_id": "asc"}],
    )
    run["runtime"] = {
        "strategies": _fetch_all_run_collection(RUNTIME_STRATEGIES_INDEX_NAME, run_id),
        "indices": _fetch_all_run_collection(RUNTIME_INDICES_INDEX_NAME, run_id),
        "scenarios": _fetch_all_run_collection(RUNTIME_SCENARIOS_INDEX_NAME, run_id),
        "judgements": _fetch_all_run_collection(RUNTIME_JUDGEMENTS_INDEX_NAME, run_id),
    }
    run["unrated_docs"] = _fetch_all_run_collection(
        UNRATED_DOCS_INDEX_NAME, run_id, sort=[{"count": "desc"}],
    )
    run["failures"] = _fetch_all_run_collection(FAILURES_INDEX_NAME, run_id)
    return run


####  Hyperparameter optimization: estimates, variants, summaries  ############
#
# Variants are stored one document per (run x strategy x variant) in the
# esrs-benchmark-runtime-variants data stream. The winner of a run is chosen
# during the run with the objective snapshotted in the run's task, because the
# holdout phase needs it. Views can re-rank variants under another objective
# from the stored tuning aggregates. That ranking is exploratory: the holdout
# scores and stored hits only exist for the run's own winner.

def _fetch_strategy_sources(candidates: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Get the _source of every candidate strategy, keyed by _id."""
    sources: Dict[str, Dict[str, Any]] = {}
    to_fetch = []
    for candidate in candidates["strategies"]:
        if candidate.get("_source"):
            sources[candidate["_id"]] = candidate["_source"]
        else:
            to_fetch.append(candidate["_id"])
    if to_fetch:
        es_response = es("studio").search(
            index="esrs-strategies",
            body={
                "query": { "ids": { "values": to_fetch }},
                "size": 10000,
                "_source": { "excludes": [ "_search" ]},
            },
        )
        for hit in es_response.body["hits"]["hits"]:
            sources[hit["_id"]] = hit["_source"]
    return sources


def _probe_latency(
        workspace_id: str,
        strategies: Dict[str, Dict[str, Any]],
        plans: Dict[str, List[Dict[str, Any]]],
        scenario_ids: List[str],
        metric_config: Dict[str, Any],
        index_pattern: str,
        n_variants: int = 3,
        n_scenarios: int = 3,
        passes: int = 2,
        errors: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
    """Time sample searches of each strategy on the content cluster.

    Samples a few variants and a few scenarios per strategy. Runs each sampled
    search `passes` times as its own single-request _rank_eval call and
    discards the first pass, so cold caches don't skew the numbers. Returns
    per-strategy {"samples", "p25_ms", "median_ms", "p75_ms"} of the wall time
    per search. A search that Elasticsearch rejects (for example, a value that
    the query doesn't accept) is appended to `errors`, once per variant, so the
    caller can surface it before the run.
    """
    reported = set()
    sample_scenarios = sorted(scenario_ids)[:n_scenarios]
    if not sample_scenarios:
        return {}
    client = es("studio")
    es_response = client.search(
        index="esrs-scenarios",
        body={ "query": { "ids": { "values": sample_scenarios }}, "size": n_scenarios, "_source": ["values"] },
    )
    scenario_values = { h["_id"]: h["_source"]["values"] for h in es_response.body["hits"]["hits"] }
    es_response = client.search(
        index="esrs-judgements",
        body={ "query": { "terms": { "scenario_id": sample_scenarios }}, "size": 10000 },
    )
    ratings: Dict[str, List[Dict[str, Any]]] = {}
    for hit in es_response.body["hits"]["hits"]:
        ratings.setdefault(hit["_source"]["scenario_id"], []).append({
            "_index": hit["_source"]["index"],
            "_id": hit["_source"]["doc_id"],
            "rating": hit["_source"]["rating"],
        })
    out = {}
    for strategy_id, source in strategies.items():
        template = { "id": strategy_id, "template": { "source": source["template"]["source"] }}
        variants = plans[strategy_id][:n_variants]
        timings: List[float] = []
        for pass_index in range(passes):
            for variant in variants:
                for scenario_id in sample_scenarios:
                    if scenario_id not in scenario_values or not ratings.get(scenario_id):
                        continue
                    params = dict(scenario_values[scenario_id])
                    if variant["values"]:
                        params["hp"] = variant["values"]
                    body = {
                        "metric": metric_config,
                        "templates": [ template ],
                        "requests": [{
                            "id": f"{strategy_id}~{variant['variant_id']}~{scenario_id}",
                            "template_id": strategy_id,
                            "params": params,
                            "ratings": ratings[scenario_id],
                        }],
                    }
                    started = time.perf_counter()
                    try:
                        es("content").rank_eval(index=index_pattern, body=body)
                    except (ConnectionError, ConnectionTimeout, ApiError) as e:
                        key = (strategy_id, variant["variant_id"])
                        if errors is not None and key not in reported:
                            reported.add(key)
                            reason = getattr(e, "message", None) or str(e)
                            errors.append(
                                f"Strategy '{source.get('name') or strategy_id}' rejected a probe search "
                                f"with hyperparameter values {utils.serialize(variant['values'])}: {reason}"
                            )
                        continue
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    if pass_index > 0:  # discard the first (cold) pass
                        timings.append(elapsed_ms)
        if timings:
            out[strategy_id] = {
                "samples": len(timings),
                "p25_ms": optimization.percentile(timings, 25),
                "median_ms": optimization.percentile(timings, 50),
                "p75_ms": optimization.percentile(timings, 75),
            }
    return out


def estimate(
        workspace_id: str,
        task: Dict[str, Any],
        probe: bool = False,
    ) -> Dict[str, Any]:
    """Estimate the cost of a benchmark run before running it (a dry run).

    Resolves the candidate strategies and scenarios of the task and returns, for
    the run as configured:

      * variants per strategy (hyperparameter values to test resolved, from
        the benchmark's values_to_test and the strategies' valid testable values)
      * the number of individual searches (not parent _rank_eval requests):
        sum(variants) x tuning scenarios x metrics, plus the holdout phase
        (the winning and baseline variant of each strategy) when the task
        reserves a holdout
      * the number of _rank_eval calls, and the limits the run must respect
        (HPO_MAX_VARIANTS, HPO_MAX_SEARCHES), with `errors` that must block the
        run and `warnings`

    If `probe` is true, also runs a short latency probe against the content
    cluster (a few variants and scenarios per strategy, each search twice with
    the first execution discarded) and extrapolates a duration range from the
    run's execution settings (`max_concurrent_searches`, `rank_eval_batch_size`,
    `rank_eval_batch_delay`). The probe puts load on the content cluster, so it
    is opt-in.

    Args:
        workspace_id: The UUID of the workspace.
        task: The benchmark task definition (see runs_create).
        probe: Whether to run the latency probe and estimate a duration.

    Returns:
        A dictionary with `strategies`, `scenarios`, `searches`,
        `rank_eval_calls`, `limits`, `warnings`, and `duration` (None unless
        probed).
    """
    task_model = TaskCreate.model_validate(task or {})
    opt = (task_model.optimization or Optimization()).model_dump()
    has_holdout = opt["holdout"]["ratio"] > 0
    metrics = task_model.metrics
    batch_size = task_model.rank_eval_batch_size or RANK_EVAL_BATCH_SIZE
    batch_delay_ms = (
        task_model.rank_eval_batch_delay
        if task_model.rank_eval_batch_delay is not None
        else RANK_EVAL_BATCH_DELAY_SEC * 1000
    )

    candidates = benchmarks.make_candidate_pool(workspace_id, task or {})
    sources = _fetch_strategy_sources(candidates)
    scenario_ids = [ c["_id"] for c in candidates["scenarios"] ]
    errors: List[str] = []
    warnings: List[str] = []

    # Count the scenarios that have judgements
    judged: List[str] = []
    if scenario_ids:
        es_response = es("studio").search(
            index="esrs-judgements",
            body={
                "query": { "terms": { "scenario_id": scenario_ids }},
                "size": 0,
                "aggs": { "scenarios": { "terms": { "field": "scenario_id", "size": len(scenario_ids) }}},
            },
        )
        judged = [ b["key"] for b in es_response.body["aggregations"]["scenarios"]["buckets"] ]
    tuning, holdout = optimization.split_scenarios(
        judged, opt["holdout"]["ratio"], opt["holdout"].get("seed") or opt.get("seed"),
    )

    # Count the variants of each strategy
    strategies_out = []
    counts = []
    plans: Dict[str, List[Dict[str, Any]]] = {}
    for strategy_id in sorted(sources):
        source = sources[strategy_id]
        entry = {
            "_id": strategy_id,
            "name": source.get("name"),
            "hyperparameters": [ h["name"] for h in (source.get("hyperparameters") or []) ],
            "variants": 1,
        }
        try:
            resolved = optimization.resolve_hyperparameters(
                source.get("hyperparameters") or [], opt["values_to_test"], strategy_id,
                opt["points_per_range"], optimize=task_model.optimization is not None,
            )
            entry["variants"] = optimization.count_variants(resolved, opt["algorithm"], opt["sample_size"])
            if probe and entry["variants"] <= optimization.MAX_VARIANTS:
                fingerprint = utils.fingerprint([ source["template"]["source"] ])
                # Sample the baseline variant and a few random ones for the probe
                plans[strategy_id] = optimization.generate_variants(
                    resolved, fingerprint, "random", 3, opt.get("seed") or "default",
                )
        except ValueError as e:
            errors.append(f"Strategy '{source.get('name') or strategy_id}': {e}")
        strategies_out.append(entry)
        counts.append(entry["variants"])

    searches = optimization.estimate_searches(counts, len(tuning), len(holdout), len(metrics))
    limits = optimization.check_limits(counts, searches["total"])
    errors.extend(limits["errors"])
    warnings.extend(limits["warnings"])
    if has_holdout and len(holdout) < optimization.MIN_STABLE_HOLDOUT_SCENARIOS:
        warnings.append(
            f"The holdout has {len(holdout)} {'scenario' if len(holdout) == 1 else 'scenarios'}, "
            f"too few to trust the result. The holdout is the scenarios kept aside to check the winner "
            f"on queries it wasn't tuned on. Aim for at least {optimization.MIN_STABLE_HOLDOUT_SCENARIOS}."
        )
    if not has_holdout and any(c > 1 for c in counts):
        warnings.append("The holdout is disabled, so scores are in-sample and optimistic.")
    if candidates["scenarios"] and not judged:
        warnings.append("None of the candidate scenarios have judgements, so the run would be skipped.")

    groups = optimization.rank_eval_groups(counts, len(tuning), len(holdout), len(metrics), batch_size)
    max_concurrent = opt.get("max_concurrent_searches") or optimization.DEFAULT_MAX_CONCURRENT_SEARCHES
    result = {
        "strategies": strategies_out,
        "scenarios": {
            "candidates": len(scenario_ids),
            "with_judgements": len(judged),
            "tuning": len(tuning),
            "holdout": len(holdout),
        },
        "metrics": len(metrics),
        "variants": sum(counts),
        "searches": searches,
        "rank_eval_calls": sum(g["calls"] for g in groups),
        "execution": {
            "max_concurrent_searches": max_concurrent,
            "rank_eval_batch_size": batch_size,
            "rank_eval_batch_delay_ms": batch_delay_ms,
        },
        "limits": {
            "max_variants": optimization.MAX_VARIANTS,
            "max_searches": optimization.MAX_SEARCHES,
        },
        "errors": errors,
        "warnings": warnings,
        "duration": None,
    }

    if probe and not errors and tuning and sources:
        workspace = es("studio").get(
            index="esrs-workspaces", id=workspace_id, source_includes=["index_pattern"],
        )
        index_pattern = workspace.body["_source"]["index_pattern"]
        k = task_model.k
        metric_config = {
            "mrr": { "mean_reciprocal_rank": { "k": k, "relevant_rating_threshold": 1 }},
            "ndcg": { "dcg": { "k": k, "normalize": True }},
            "precision": { "precision": { "k": k, "ignore_unlabeled": False }},
            "recall": { "recall": { "k": k }},
        }[metrics[0]]
        probed = _probe_latency(
            workspace_id, sources, plans, tuning, metric_config, index_pattern,
            errors=warnings,
        )
        sorted_ids = sorted(sources)
        known = [ p for p in probed.values() ]
        fallback = (
            (sum(p["p25_ms"] for p in known) / len(known), sum(p["p75_ms"] for p in known) / len(known))
            if known else None
        )
        latency = []
        for strategy_id in sorted_ids:
            p = probed.get(strategy_id)
            latency.append((p["p25_ms"], p["p75_ms"]) if p else fallback)
        if all(x is not None for x in latency):
            duration = optimization.estimate_duration_ms(
                groups, latency, max_concurrent, batch_size, batch_delay_ms,
            )
            result["duration"] = {
                **duration,
                "probe": probed,
                "note": (
                    "The estimate extrapolates a small sample. Variants of a run execute concurrently "
                    "and compete for the same resources, so real latencies can be higher."
                ),
            }
        else:
            warnings.append("The latency probe returned no timings, so no duration estimate is available.")
    return result


def _task_objective(run: Dict[str, Any]) -> Dict[str, Any]:
    """The objective and constraint snapshotted in a run's task."""
    optimization_task = (run.get("task") or {}).get("optimization") or {}
    metrics = (run.get("task") or {}).get("metrics") or ["ndcg"]
    objective = optimization_task.get("objective") or {
        "metric": "ndcg" if "ndcg" in metrics else metrics[0],
        "aggregation": "mean",
    }
    return {
        "objective": objective,
        "latency_constraint": optimization_task.get("latency_constraint"),
        "holdout_ratio": (optimization_task.get("holdout") or {}).get("ratio") or 0,
    }


def _sort_variants(variants: List[Dict[str, Any]], sort: str, descending: bool) -> List[Dict[str, Any]]:
    """Sort a variants table by `rank`, `took`, `coverage`, `hp:<name>`, or
    `metric:<name>`. Variants without a value for the sort key stay last."""
    def value(v):
        tuning = (v.get("aggregates") or {}).get("tuning") or {}
        if sort.startswith("hp:"):
            return v["values"].get(sort[3:])
        if sort.startswith("metric:"):
            m = (tuning.get("metrics") or {}).get(sort[7:])
            return m["avg"] if m else None
        if sort == "took":
            return (tuning.get("took") or {}).get("median")
        if sort == "coverage":
            return tuning.get("coverage")
        return v["rank"]
    present = [ v for v in variants if value(v) is not None ]
    missing = [ v for v in variants if value(v) is None ]
    present.sort(key=value, reverse=descending)
    return present + missing


def _rank_stored_variants(
        variants: List[Dict[str, Any]],
        objective: Dict[str, Any],
        constraint: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
    """Rank stored variant docs by their tuning aggregates."""
    ranked = optimization.rank_variants(
        [{ **v, "aggregates": (v.get("aggregates") or {}).get("tuning") or {} } for v in variants],
        objective,
        constraint,
    )
    by_id = { v["variant_id"]: v for v in variants }
    out = []
    for r in ranked:
        stored = by_id[r["variant_id"]]
        out.append({
            **{ k: v for k, v in stored.items() if k not in ("score", "rank", "violates_constraint", "is_winner") },
            "is_run_winner": bool(stored.get("is_winner")),
            "is_winner": r["is_winner"],
            "score": r["score"],
            "rank": r["rank"],
            "violates_constraint": r["violates_constraint"],
        })
    return out


def get_variants(
        run_id: str,
        strategy_id: str,
        objective: Optional[Dict[str, Any]] = None,
        latency_constraint: Optional[Dict[str, Any]] = None,
        sort: str = "rank",
        descending: bool = False,
        size: int = 25,
        page: int = 1,
    ) -> Dict[str, Any]:
    """Get a page of the hyperparameter variants of one strategy in a run.

    Each item has the variant's `variant_id`, hyperparameter `values`, `score`
    (the objective), `rank`, `is_winner`, `violates_constraint`, `is_baseline`,
    `hits_stored`, and `aggregates` ({tuning, holdout}, each with metrics,
    latency, and judgement coverage).

    Variants rank under the run's own objective by default. Pass `objective`
    ({metric, aggregation}) and/or `latency_constraint` ({stat, max_ms}) to
    re-rank without re-running the benchmark. A re-ranking is `exploratory`:
    it uses only tuning scores, and holdout scores and hits exist only for the
    run's own winner and baseline variants (flagged `is_run_winner`).

    Args:
        run_id: The UUID of the run.
        strategy_id: The _id of the strategy.
        objective: Optional objective override, e.g. {"metric": "mrr", "aggregation": "mean"}.
        latency_constraint: Optional constraint override, e.g. {"stat": "median", "max_ms": 50}.
        sort: `rank` (default), `took`, `coverage`, `hp:<name>`, or `metric:<name>`.
        descending: Whether to sort descending.
        size: Number of variants per page.
        page: Page number.

    Returns:
        {run_id, strategy_id, total, size, page, hyperparameters, ranking, items}.
    """
    run = get(run_id)["_source"]
    defaults = _task_objective(run)
    effective_objective = objective or defaults["objective"]
    effective_constraint = latency_constraint if latency_constraint is not None else defaults["latency_constraint"]
    exploratory = (
        effective_objective != defaults["objective"]
        or effective_constraint != defaults["latency_constraint"]
    )
    variants = _fetch_all_run_collection(
        RUNTIME_VARIANTS_INDEX_NAME, run_id,
        extra_filters=[{ "term": { "strategy_id": strategy_id }}],
    )
    ranked = _rank_stored_variants(variants, effective_objective, effective_constraint)
    if sort != "rank" or descending:
        ranked = _sort_variants(ranked, sort, descending)
    snapshot = _paginate_run_collection(
        RUNTIME_STRATEGIES_INDEX_NAME, run_id, size=1, page=1,
        extra_filters=[{ "term": { "strategy_id": strategy_id }}],
    )["items"]
    hyperparameters = (snapshot[0]["item"].get("_resolved_hyperparameters") if snapshot else None) or []
    start = max(0, (page - 1) * size)
    return {
        "run_id": run_id,
        "strategy_id": strategy_id,
        "total": len(ranked),
        "size": size,
        "page": page,
        "hyperparameters": hyperparameters,
        "ranking": {
            "objective": effective_objective,
            "latency_constraint": effective_constraint,
            "exploratory": exploratory,
        },
        "items": ranked[start:start + size],
    }


def get_variant(run_id: str, variant_id: str, strategy_id: Optional[str] = None) -> Dict[str, Any]:
    """Get one stored variant of a run by its `variant_id`.

    Two strategies with identical templates and values share a variant ID, so
    pass `strategy_id` to disambiguate. Raises ValueError if the variant isn't
    found or is ambiguous.
    """
    filters = [{ "term": { "variant_id": variant_id }}]
    if strategy_id:
        filters.append({ "term": { "strategy_id": strategy_id }})
    found = _paginate_run_collection(RUNTIME_VARIANTS_INDEX_NAME, run_id, size=2, page=1, extra_filters=filters)
    if not found["items"]:
        raise ValueError(f"variant '{variant_id}' not found in run '{run_id}'")
    if len(found["items"]) > 1:
        raise ValueError(f"variant '{variant_id}' belongs to more than one strategy, so strategy_id is required")
    return found["items"][0]


def get_runtime_strategy(run_id: str, strategy_id: str) -> Dict[str, Any]:
    """Get the runtime snapshot of one strategy in a run (its `item` is the
    strategy as it was when the run ran)."""
    found = _paginate_run_collection(
        RUNTIME_STRATEGIES_INDEX_NAME, run_id, size=1, page=1,
        extra_filters=[{ "term": { "strategy_id": strategy_id }}],
    )
    if not found["items"]:
        raise ValueError(f"strategy '{strategy_id}' not found in run '{run_id}'")
    return found["items"][0]


def _compact_variant(v: Dict[str, Any], objective: Dict[str, Any]) -> Dict[str, Any]:
    aggregates = v.get("aggregates") or {}
    tuning = aggregates.get("tuning") or {}
    holdout = aggregates.get("holdout")
    def rounded(x):
        return round(x, 4) if isinstance(x, (int, float)) else x
    return {
        "variant_id": v["variant_id"],
        "values": v["values"],
        "is_baseline": v.get("is_baseline", False),
        "score": rounded(v.get("score")),
        "holdout_score": rounded(optimization.objective_score(holdout, objective)) if holdout else None,
        "took_median_ms": rounded((tuning.get("took") or {}).get("median")),
        "coverage": rounded(tuning.get("coverage")),
        "violates_constraint": v.get("violates_constraint", False),
    }


def get_optimization_summary(run_id: str, top_n: int = 5) -> Dict[str, Any]:
    """Get a compact hyperparameter optimization summary of a run.

    Built for agents. Per strategy it returns the variant count, the winner and
    baseline variants, the top N variants, a per-hyperparameter sensitivity
    summary, and warnings, instead of the full list of variants. Use
    `runs_get_variants` to drill into a strategy.

    Scores are the objective of the run (see `objective`). `holdout_score` is
    the headline when `score_basis` is `holdout`. Without a holdout, scores are
    in-sample and optimistic. `sensitivity[].spread` is the gap between the
    best and worst mean score across a hyperparameter's values (a small spread
    means the hyperparameter barely matters), and `points` are [value, mean
    score] pairs.

    Args:
        run_id: The UUID of the run.
        top_n: Number of top variants to return per strategy.

    Returns:
        {run_id, objective, latency_constraint, score_basis, scenarios, strategies}.
    """
    run = get(run_id)["_source"]
    defaults = _task_objective(run)
    objective, constraint = defaults["objective"], defaults["latency_constraint"]
    variants = _fetch_all_run_collection(RUNTIME_VARIANTS_INDEX_NAME, run_id)
    snapshots = get_runtime_strategies(run_id)["items"]

    # Count scenarios per split
    scenarios = { "tuning": 0, "holdout": 0 }
    try:
        es_response = es("studio").search(
            index=RUNTIME_SCENARIOS_INDEX_NAME,
            body={
                "query": { "bool": { "filter": [{ "term": { "run_id": run_id }}] }},
                "size": 0,
                "aggs": { "split": { "terms": { "field": "split", "size": 5 }}},
            },
        )
        for bucket in es_response.body["aggregations"]["split"]["buckets"]:
            scenarios[bucket["key"]] = bucket["doc_count"]
    except NotFoundError:
        pass
    has_holdout = scenarios["holdout"] > 0
    basis = "holdout" if has_holdout else "in_sample"

    strategies_out = []
    for snapshot in sorted(snapshots, key=lambda s: s["strategy_id"]):
        strategy_id = snapshot["strategy_id"]
        item = snapshot.get("item") or {}
        own = [ v for v in variants if v["strategy_id"] == strategy_id ]
        if not own:
            continue
        ranked = _rank_stored_variants(own, objective, constraint)
        run_winner = next((v for v in ranked if v["is_run_winner"]), ranked[0])
        baseline = next((v for v in ranked if v.get("is_baseline")), None)
        warnings = []
        coverage = ((run_winner.get("aggregates") or {}).get("tuning") or {}).get("coverage")
        if coverage is not None and coverage < optimization.LOW_COVERAGE_THRESHOLD:
            warnings.append(
                f"The winner's judgement coverage is {coverage:.0%}. Unrated documents count as irrelevant, "
                "which biases scores against variants that surface different documents. Judge the unrated documents."
            )
        if not has_holdout and len(own) > 1:
            warnings.append("No holdout: scores are in-sample and optimistic.")
        if has_holdout and scenarios["holdout"] < optimization.MIN_STABLE_HOLDOUT_SCENARIOS:
            n_holdout = scenarios["holdout"]
            warnings.append(
                f"The holdout has only {n_holdout} {'scenario' if n_holdout == 1 else 'scenarios'}, "
                "too few for stable scores."
            )
        if len(own) > 1 and not any(v["is_run_winner"] and not v["violates_constraint"] for v in ranked):
            warnings.append("No variant satisfies the latency constraint, so the baseline variant is the winner.")
        winner_holdout = optimization.objective_score((run_winner.get("aggregates") or {}).get("holdout"), objective) \
            if (run_winner.get("aggregates") or {}).get("holdout") else None
        baseline_holdout = optimization.objective_score((baseline.get("aggregates") or {}).get("holdout"), objective) \
            if baseline and (baseline.get("aggregates") or {}).get("holdout") else None
        if winner_holdout is not None and baseline_holdout is not None and run_winner is not baseline \
                and winner_holdout <= baseline_holdout:
            warnings.append("Tuning did not help on the holdout: the winner scores no better than the baseline.")
        sensitivity = optimization.sensitivity(ranked, item.get("_resolved_hyperparameters") or [])
        strategies_out.append({
            "strategy_id": strategy_id,
            "name": item.get("name"),
            "variant_count": len(own),
            "winner": _compact_variant(run_winner, objective),
            "baseline": _compact_variant(baseline, objective) if baseline else None,
            "top_variants": [ _compact_variant(v, objective) for v in ranked[:max(0, top_n)] ],
            "sensitivity": [
                {
                    "name": s["name"],
                    "kind": s["kind"],
                    "spread": round(s["spread"], 4),
                    "points": [[ p["value"], round(p["mean"], 4) ] for p in s["points"]],
                }
                for s in sorted(sensitivity, key=lambda s: -s["spread"])
            ],
            "warnings": warnings,
        })
    return {
        "run_id": run_id,
        "objective": objective,
        "latency_constraint": constraint,
        "score_basis": basis,
        "scenarios": scenarios,
        "note": "Variants of a run execute concurrently and compete for resources, so latency comparisons are noisy.",
        "strategies": strategies_out,
    }


def create(
        workspace_id: str,
        benchmark_id: str,
        task: Dict[str, Any],
        user: str = None,
        via: str = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
    """Create a pending run for a given workspace and benchmark.

    With `dry_run`, validate the task and return the cost estimate of the run
    (variants, individual searches, _rank_eval calls, limits, warnings) instead
    of creating it, so you can check the cost before committing to a run. See
    `estimate`. The duration probe is not part of a dry run.

    Args:
        workspace_id: The UUID of the workspace.
        benchmark_id: The UUID of the benchmark.
        task: The run task definition.
        user: The username of the creator.
        dry_run: If true, estimate the cost of the run and don't create it.

    Returns:
        The response from the Elasticsearch index operation, or the estimate
        when `dry_run` is true.
    """
    
    # Create, validate, and dump model
    doc = {
        "workspace_id": workspace_id,
        "benchmark_id": benchmark_id,
        "task": task
    }
    doc = RunCreate.model_validate(doc, context={"user": user, "via": via}).serialize()
    if dry_run:
        return estimate(workspace_id, task)
    
    client = es("studio")
    es_response = client.index(
        index=INDEX_NAME,
        id=utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def _delete_stream_docs_by_run_ids(client, run_ids: List[str]) -> None:
    """Delete results/forensics data-stream docs for the given run_ids.

    delete_by_query against a data stream removes matching documents (it does
    not remove backing indices; DLM handles those). Safe no-op if the streams
    do not exist yet.
    """
    if not run_ids:
        return
    body = { "query": { "terms": { "run_id": run_ids }}}
    for stream in RUN_DATA_STREAMS:
        try:
            client.delete_by_query(
                index=stream, body=body, refresh=True, conflicts="proceed",
            )
        except NotFoundError:
            # Stream not created yet (e.g. only skipped runs so far) — nothing to delete.
            pass


def delete(_id: str) -> Dict[str, Any]:
    """Delete a run and its results/forensics from Elasticsearch.

    Args:
        _id: The UUID of the run.

    Returns:
        The response from the Elasticsearch delete operation on the run doc.
    """
    client = es("studio")
    # Remove the run's immutable results/forensics first, then the run doc.
    _delete_stream_docs_by_run_ids(client, [_id])
    es_response = client.delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True,
    )
    return es_response

def cleanup(time_ago: str = "2h") -> Dict[str, Any]:
    """Delete stale "running" runs and their orphaned results/forensics.

    A run that crashed mid-flight is left "running"; sweeping it must also remove
    any results/forensics documents already written for that run_id, otherwise
    orphans accumulate forever in the append-only data streams.

    Args:
        time_ago: A relative time string (e.g., "2h") defining what is considered stale.

    Returns:
        The response from the Elasticsearch delete_by_query operation on the run docs.
    """
    client = es("studio")

    # Identify the stale running runs first so we can clean their stream docs by
    # run_id before deleting the run docs themselves.
    stale_query = {
        "bool": {
            "must": [
                { "term": { "@meta.status": "running" }},
                { "range": { "@meta.started_at": { "lt": f"now-{time_ago}" }}}
            ]
        }
    }
    stale_ids: List[str] = []
    try:
        found = client.search(
            index=INDEX_NAME,
            body={"query": stale_query, "_source": False, "size": 10000},
        )
        stale_ids = [hit["_id"] for hit in found.body["hits"]["hits"]]
    except NotFoundError:
        stale_ids = []

    _delete_stream_docs_by_run_ids(client, stale_ids)

    es_response = client.delete_by_query(
        index=INDEX_NAME,
        body={"query": stale_query},
        refresh=True,
        conflicts="proceed",
    )
    return es_response
    