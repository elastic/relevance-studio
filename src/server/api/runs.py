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
from . import benchmarks, content
from .. import utils
from ..client import es

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch
from ..models import (
    RunComplete,
    RunCreate,
    RunFail,
    RunSkip,
    BenchmarkResult,
    BenchmarkForensics,
)
from elasticsearch import helpers

INDEX_NAME = "esrs-benchmark-runs"
CONFIGS_INDEX_NAME = "esrs-benchmark-configs"
RESULTS_INDEX_NAME = "esrs-benchmark-results"
FORENSICS_INDEX_NAME = "esrs-benchmark-forensics"
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
        A dictionary containing aggregated 'metrics' and 'unrated_docs' statistics.
    """
    metrics = {}
    unrated_count = 0
    total_hits = 0
    
    # Group metrics by metric name
    metric_values = {}
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
    return {
        'metrics': metrics,
        'unrated_docs': unrated_docs
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
            doc = BenchmarkResult.model_validate({
                "run_id": run_id,
                "workspace_id": workspace_id,
                "benchmark_id": benchmark_id,
                "strategy_id": strategy_id,
                "scenario_id": scenario_id,
                "metrics": search.get("metrics") or {},
                "hits": search.get("hits") or [],
                "@timestamp": stopped_at,
            }).serialize()
            actions.append({
                "_op_type": "create",
                "_index": RESULTS_INDEX_NAME,
                "_id": utils.unique_id([run_id, strategy_id, scenario_id]),
                "_source": doc,
            })

    # Exactly one forensics document per run (runtime + unrated_docs + per-strategy
    # failures). Always written for completed/failed runs so forensics count
    # tracks run count.
    failures = [
        {"strategy_id": r.get("strategy_id"), "failures": r.get("failures")}
        for r in (evaluation.get("results") or [])
        if r.get("failures")
    ]
    forensics_input: Dict[str, Any] = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "benchmark_id": benchmark_id,
        "@timestamp": stopped_at,
    }
    if evaluation.get("runtime") is not None:
        forensics_input["runtime"] = evaluation["runtime"]
    if evaluation.get("unrated_docs") is not None:
        forensics_input["unrated_docs"] = evaluation["unrated_docs"]
    if failures:
        forensics_input["failures"] = failures
    forensics_doc = BenchmarkForensics.model_validate(forensics_input).serialize()
    actions.append({
        "_op_type": "create",
        "_index": FORENSICS_INDEX_NAME,
        "_id": utils.unique_id([run_id, "forensics"]),
        "_source": forensics_doc,
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
        evaluation: The evaluation configuration to run.
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

    try:
    
        # Parse and validate request
        workspace_id = evaluation["workspace_id"]
        
        # Select candidates for strategies and scenarios
        candidates = benchmarks.make_candidate_pool(workspace_id, evaluation["task"])
        
        # If there are no strategies or scenarios that meet the criteria of the
        # benchmark task definition, mark the evaluation as "skipped" and exit.
        if not candidates["strategies"] or not candidates["scenarios"]:
            if store_results:
                doc_updates = {
                    "took": int((time.time() - started_at) * 1000)
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
        for hit in hits:
            template = hit["_source"]["template"]["source"]
            _rank_eval["templates"].append({
                "id": hit["_id"],
                "template": {
                    "source": template
                }
            })
            runtime_strategy = {
                "_fingerprint": utils.fingerprint([ template ])
            }
            for field, value in hit["_source"].items():
                if field == "workspace_id":
                    continue
                runtime_strategy[field] = value
            evaluation["runtime"]["strategies"][hit["_id"]] = runtime_strategy
        
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
        
        # Track results by strategy and scenarios.
        # Failures are stored at the strategy level because not all errors can
        # be linked to a specific scenario.
        _results = {}
        for strategy_id in evaluation["strategy_id"]:
            _results[strategy_id] = {
                "scenarios": {},
                "failures": []
            }
            for scenario_id in evaluation["scenario_id"]:
                _results[strategy_id]["scenarios"][scenario_id] = {
                    "metrics": {},
                    "hits": []
                }
        
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
        if not scenarios_with_ratings:
            # If no scenarios have ratings, mark evaluation as skipped
            evaluation["took"] = int((time.time() - started_at) * 1000)
            if store_results:
                # Skipped: no scored results and no runtime snapshot to persist;
                # write only the run doc's terminal status. Strip any heavy
                # fields so they never land on the small run doc.
                skip_doc = RunSkip.model_validate(evaluation).serialize()
                for heavy in ("results", "runtime", "unrated_docs"):
                    skip_doc.pop(heavy, None)
                client.update(
                    index=INDEX_NAME,
                    id=evaluation_id,
                    doc=skip_doc,
                    refresh=True
                )
            return evaluation
        
        # Create a set of requests for each evaluation metric
        for m in evaluation["task"]["metrics"]:
            
            # Run rank_eval one strategy at a time to scale for larger benchmarks
            for template in _rank_eval["templates"]:
            
                # Reset the metric and requests for this iterartion
                _rank_eval["metric"] = {}
                _rank_eval["requests"] = []
                
                # Define the metric for this iteration
                metric_name = metrics_config[m]["name"]
                _rank_eval["metric"][metric_name] = metrics_config[m]["config"]
                
                # Define requests for each combination of strategies and scenarios
                grid = list(itertools.product([
                    template["id"]], # strategy_id
                    evaluation["scenario_id"], # scenario_id
                ))
                for strategy_id, scenario_id in grid:
                    # Skip scenarios that have no ratings/judgements
                    if scenario_id not in ratings or not ratings[scenario_id]:
                        continue
                        
                    _rank_eval["requests"].append({
                        "id": f"{strategy_id}~{scenario_id}",
                        "template_id": strategy_id,
                        "params": scenarios[scenario_id],
                        "ratings": ratings[scenario_id]
                    })
                    
                # Skip if no valid requests (all scenarios have no ratings)
                if not _rank_eval["requests"]:
                    continue

                # Batch the requests to avoid overwhelming Elasticsearch
                all_requests = _rank_eval["requests"]
                for batch_index, batch_requests in enumerate(utils.chunks(all_requests, benchmark_batch_size)):

                    # Throttle between batches
                    if batch_index > 0 and benchmark_batch_delay_sec > 0:
                        time.sleep(benchmark_batch_delay_sec)

                    # Run _rank_eval on the content deployment and accumulate the results
                    body = {
                        "metric": _rank_eval["metric"],
                        "requests": batch_requests,
                        "templates": [ template, ]
                    }
                    es_response = None
                    rank_eval_requests_count += len(batch_requests)
                    try:
                        es_response = es("content").rank_eval(
                            index=index_pattern,
                            body=body
                        )
                    except (ConnectionError, ConnectionTimeout, ApiError) as e:
                        _results[template["id"]]["failures"].append({
                            "scenario_id": None,
                            "metric": m,
                            "error": {
                                "type": e.__class__.__name__,
                                "reason": str(e)
                            }
                        })
                        continue

                    # Store results
                    for request_id, details in es_response.body["details"].items():
                        strategy_id, scenario_id = request_id.split("~", 1)
                        _results[strategy_id]["scenarios"][scenario_id]["metrics"][m] = details["metric_score"]
                        if not len(_results[strategy_id]["scenarios"][scenario_id]["hits"]):
                            _results[strategy_id]["scenarios"][scenario_id]["hits"] = details["hits"]
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
                                        "scenarios": set()
                                    }
                                _unrated_docs[_index][_id]["count"] += 1
                                _unrated_docs[_index][_id]["strategies"].add(strategy_id)
                                _unrated_docs[_index][_id]["scenarios"].add(scenario_id)

                    # Store failures
                    if es_response.body.get("failures"):
                        for request_id, failure in es_response.body["failures"].items():
                            strategy_id, scenario_id = request_id.split("~", 1)
                            _results[strategy_id]["failures"].append({
                                "scenario_id": scenario_id,
                                "metric": m,
                                "error": failure.get("error") or failure
                            })
            
        # Restructure results for response
        evaluation["results"] = []
        for strategy_id, _strategy_results in _results.items():
            strategy_results = {
                "strategy_id": strategy_id,
                "searches": [],
                "failures":  _results[strategy_id]["failures"],
            }
            for scenario_id, _scenario_results in _strategy_results["scenarios"].items():
                scenario_results = {
                    "scenario_id": scenario_id,
                    "metrics": _scenario_results["metrics"],
                    "hits": _scenario_results["hits"]
                }
                strategy_results["searches"].append(scenario_results)
            evaluation["results"].append(strategy_results)
        
        # Restructure unrated_docs for response
        unrated_docs = []
        for _index in sorted(_unrated_docs.keys()):
            for _id in sorted(_unrated_docs[_index].keys()):
                doc = _unrated_docs[_index][_id]
                strategies = sorted(list(doc["strategies"]))
                scenarios = sorted(list(doc["scenarios"]))
                unrated_docs.append({
                    "_index": _index,
                    "_id": _id,
                    "count": doc["count"],
                    "strategies": strategies,
                    "scenarios": scenarios
                })
        evaluation["unrated_docs"] = sorted(unrated_docs, key=lambda doc: doc["count"], reverse=True)
        
        # Summarize metrics
        evaluation["summary"] = generate_summary(
            evaluation,
            candidates["strategies"],
            candidates["scenarios"]
        )
        evaluation["task"]["requests"] = rank_eval_requests_count
        
        # Create final response
        stopped_at = time.time()
        evaluation["took"] = int(( stopped_at - started_at) * 1000)
        doc = RunComplete.model_validate(evaluation).serialize()

        # Store results
        if store_results:
            # Write results + forensics into the data streams BEFORE flipping the
            # run doc's terminal status, so the run doc's status is the single
            # source of truth for "this run's data is complete and trustworthy."
            _write_results_and_forensics(doc, evaluation_id)

            # The run doc itself stays small: strip the heavy fields that now live
            # in the data streams before writing it.
            run_doc = {k: v for k, v in doc.items() if k not in ("results", "runtime", "unrated_docs")}
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
        doc = RunFail.model_validate(evaluation).serialize()
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
            run_doc = {k: v for k, v in doc.items() if k not in ("results", "runtime", "unrated_docs")}
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

    Returns the small run document (status, task, summary, error, took). The
    heavy per-search results and the runtime/unrated-docs audit trail are NOT on
    this document; fetch them from the results stream or via get_forensics().

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

# Field paths within the forensics document that may be fetched selectively.
# The runtime snapshot is split so callers can pull the small, bounded
# name/tag metadata (strategies, scenarios) without the large `runtime.judgements`
# map, which scales with every rated document across every scenario.
FORENSICS_PARTS = set([
    "runtime",              # the whole runtime snapshot (large: includes judgements)
    "runtime.indices",
    "runtime.scenarios",
    "runtime.strategies",
    "runtime.judgements",   # the largest field; scales with rated docs
    "unrated_docs",
    "failures",
])

# Fields always returned regardless of `parts` (cheap identifiers/timestamp),
# so every response is self-describing.
_FORENSICS_ALWAYS = ["run_id", "workspace_id", "benchmark_id", "@timestamp"]


def get_forensics(run_id: str, parts: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get the forensics audit document for a run, optionally field-selective.

    The forensics data lives in the esrs-benchmark-forensics data stream (one
    document per run), keyed by run_id. It is read-rarely and can be large (the
    `runtime.judgements` snapshot scales with the number of rated documents), so
    callers should request only the parts they need:

      * Summary table / heatmap -> ["runtime.strategies", "runtime.scenarios"]
        (small, bounded by the number of assets, not by judgements)
      * Runtime-assets flyout / full download -> ["runtime"] (or None for all)
      * Unrated-docs / judgement-gap-fill -> ["unrated_docs"]

    Args:
        run_id: The UUID of the run.
        parts: Optional list of forensics field paths to include (see
            FORENSICS_PARTS). When omitted/empty, the full document is returned
            (back-compatible). Unknown parts are ignored.

    Returns:
        A dict shaped like a single-doc get: {"_id", "found", "_source"}. The
        `_source` always carries the identifiers + @timestamp, plus whichever
        requested parts exist. `found` is False if no forensics exist (e.g. a
        skipped run, which writes none).
    """
    client = es("studio")

    source_includes = None
    if parts:
        requested = [p for p in parts if p in FORENSICS_PARTS]
        # Always include cheap identifiers so the response is self-describing.
        source_includes = _FORENSICS_ALWAYS + requested

    body = {"query": {"term": {"run_id": run_id}}, "size": 1}
    if source_includes is not None:
        body["_source"] = {"includes": source_includes}

    try:
        es_response = client.search(index=FORENSICS_INDEX_NAME, body=body)
    except NotFoundError:
        return {"_id": run_id, "found": False, "_source": {}}
    hits = es_response.body.get("hits", {}).get("hits", [])
    if not hits:
        return {"_id": run_id, "found": False, "_source": {}}
    return {"_id": run_id, "found": True, "_source": hits[0]["_source"]}

def create(
        workspace_id: str,
        benchmark_id: str,
        task: Dict[str, Any],
        user: str = None,
        via: str = None,
    ) -> Dict[str, Any]:
    """Create a pending evaluation for a given workspace and benchmark.

    Args:
        workspace_id: The UUID of the workspace.
        benchmark_id: The UUID of the benchmark.
        task: The evaluation task definition.
        user: The username of the creator.

    Returns:
        The response from the Elasticsearch index operation.
    """
    
    # Create, validate, and dump model
    doc = {
        "workspace_id": workspace_id,
        "benchmark_id": benchmark_id,
        "task": task
    }
    doc = RunCreate.model_validate(doc, context={"user": user, "via": via}).serialize()
    
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
    for stream in (RESULTS_INDEX_NAME, FORENSICS_INDEX_NAME):
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
    