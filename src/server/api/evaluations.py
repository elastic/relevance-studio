# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import itertools
import time
import traceback
from typing import Any, Dict, List, Optional
import logging

# Elastic packages
from elastic_transport import ConnectionError, ConnectionTimeout
from elasticsearch import ApiError

# App packages
from . import benchmarks, content
from .. import utils
from ..client import es
from ..models import (
    EvaluationComplete,
    EvaluationCreate,
    EvaluationFail,
    EvaluationSkip,
)

INDEX_NAME = "esrs-evaluations"
SEARCH_FIELDS = utils.get_search_fields_from_mapping("evaluations")
VALID_METRICS = set([ "mrr", "ndcg", "precision", "recall" ])

logger = logging.getLogger(__name__)

def _generate_summary_metrics(searches_list):
    """
    Calculate aggregated metrics from a list of search results.
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
    """
    Generate summary statistics from evaluation results.
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

def run(
        evaluation: Dict[str, Any],
        store_results: Optional[bool] = False,
        started_by = "unknown",
    ) -> Dict[str, Any]:
    """
    Executes an evaluation for a benchmark.
    """
    
    # Start timer
    started_at = time.time()
    evaluation["@meta"] = {
        "started_at": utils.timestamp(started_at),
        "started_by": started_by,
    }
    evaluation_id = evaluation.pop("_id", None)
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
                doc_updates = EvaluationSkip.model_validate(doc_updates).serialize()
                es_response = es("studio").update(
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
        es_response = es("studio").get(
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
                "query": { "ids": { "values": evaluation["strategy_id"] }},
                "size": size,
                "version": True,
                "_source": { "excludes": [ "_search" ]},
            }
            es_response = es("studio").search(
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
        es_response = es("studio").search(
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
        es_response = es("studio").search(
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
                es("studio").update(
                    index=INDEX_NAME,
                    id=evaluation_id,
                    doc=EvaluationSkip.model_validate(evaluation).serialize(),
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
                
                # Debug: Print request structure
                print(f"Rank eval request for strategy {template['id']}:")
                print(f"  Templates: {len(_rank_eval['templates'])}")
                print(f"  Requests: {len(_rank_eval['requests'])}")
                print(f"  Metric: {_rank_eval['metric']}")
                    
                # Run _rank_eval on the content deployment and accumulate the results
                body = {
                    "metric": _rank_eval["metric"],
                    "requests": _rank_eval["requests"],
                    "templates": [ template, ]
                }
                es_response = None
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
        
        # Create final response
        stopped_at = time.time()
        evaluation["took"] = int(( stopped_at - started_at) * 1000)
        doc = EvaluationComplete.model_validate(evaluation).serialize()
        
        # Store results
        if store_results:
            es_response = es("studio").update(
                index="esrs-evaluations",
                id=evaluation_id,
                doc=doc,
                refresh=True
            )
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
        doc = EvaluationFail.model_validate(evaluation).serialize()
        if store_results:
            es("studio").update(
                index="esrs-evaluations",
                id=evaluation_id,
                doc=doc,
                refresh=True
            )
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
    """
    Search for evaluations.
    """
    filters = [{ "term": { "benchmark_id": benchmark_id }}]
    response = utils.search_assets(
        "evaluations", workspace_id, text, filters, sort, size, page
    )
    return response

def get(_id: str) -> Dict[str, Any]:
    """
    Get an evaluation by its _id.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(
        workspace_id: str,
        benchmark_id: str,
        task: Dict[str, Any],
        user: str = None,
    ) -> Dict[str, Any]:
    """
    Create a pending evaluation for a given workspace_id and benchmark_id.
    """
    
    # Create, validate, and dump model
    doc = {
        "workspace_id": workspace_id,
        "benchmark_id": benchmark_id,
        "task": task
    }
    doc = EvaluationCreate.model_validate(doc, context={"user": user}).serialize()
    
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def delete(_id: str) -> Dict[str, Any]:
    """
    Delete an evaluation in Elasticsearch.
    """
    es_response = es("studio").delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True,
    )
    return es_response

def cleanup(time_ago: str = "2h") -> Dict[str, Any]:
    """
    Delete stale evaluations in Elasticsearch, which have had a status of
    "running" for too long of a time.
    """
    body = {
        "query": {
            "bool": {
                "must": [
                    { "term": { "@meta.status": "running" }},
                    { "range": { "@meta.started_at": { "lt": f"now-{time_ago}" }}}
                ]
            }
        }
    }
    es_response = es("studio").delete_by_query(
        index=INDEX_NAME,
        body=body,
        refresh=True,
    )
    return es_response
    