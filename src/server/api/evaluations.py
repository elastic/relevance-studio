# Standard packages
import itertools
import time
from typing import Any, Dict, Optional

# App packages
from . import benchmarks, content
from .. import utils
from ..client import es

INDEX_NAME = "esrs-evaluations"
VALID_METRICS = set([ "ndcg", "precision", "recall" ])

def validate_k(value):
    if not (isinstance(value, int) and not isinstance(value, bool)):
        raise Exception("\"k\" must be an integer")
    if value < 1:
        raise Exception("\"k\" must be greater than 0")
    
def validate_metrics(value):
    if not(isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value)):
        raise Exception("\"metrics\" must be a list of strings")
    for metric in value:
        if metric not in VALID_METRICS:
            raise Exception(f"\"metrics\" only supports these values: {', '.join(sorted(VALID_METRICS))}")

def run(
        evaluation: Dict[str, Any],
        store_results: Optional[bool] = False
    ) -> Dict[str, Any]:
    """
    Executes an evaluation for a benchmark.
    """
    
    # Start timer
    started_at = time.time()
    evaluation["@meta"]["started_at"] = utils.timestamp(started_at)
    evaluation_id = evaluation.pop("_id")
    try:
    
        # Parse and validate request
        project_id = evaluation["project_id"]
        benchmark_id = evaluation["benchmark_id"]
        validate_k(evaluation["task"].get("k"))
        validate_metrics(evaluation["task"].get("metrics"))
        
        # Select candidates for strategies and scenarios
        candidates = benchmarks.make_candidate_pool(project_id, evaluation["task"])
        
        # If there are no strategies or scenarios that meet the criteria of the
        # benchmark task definition, mark the evaluation as "skipped" and exit.
        if not candidates["strategies"] or not candidates["scenarios"]:
            doc_updates = {
                "@meta": {
                    "status": "skipped",
                    "stopped_at": utils.timestamp()
                }
            }
            es_response = es("studio").update(
                index=INDEX_NAME,
                id=evaluation_id,
                doc=doc_updates,
                refresh=True
            )
            return es_response
        
        # Track the strategies and scenarios that were selected for this evaluation
        evaluation["strategy_id"] = candidates["strategies"]
        evaluation["scenario_id"] = candidates["scenarios"]
        del candidates
        
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
        
        # Get the index pattern and rating scale of project
        es_response = es("studio").get(
            index="esrs-projects",
            id=project_id,
            source_includes=["index_pattern","rating_scale"]
        )
        index_pattern = es_response.body["_source"]["index_pattern"]
        # TODO: rating_scale_max will be used when implementing the err metric
        rating_scale_max = es_response.body["_source"]["rating_scale"]["max"]
        
        # Get the strategies, add them to "templates" in _rank_eval, and track
        # their original contents
        body = {
            "query": { "ids": { "values": evaluation["strategy_id"] }},
            "size": size,
            "version": True
        }
        es_response = es("studio").search(
            index="esrs-strategies",
            body=body
        )
        for hit in es_response.body["hits"]["hits"]:
            _rank_eval["templates"].append({
                "id": hit["_id"],
                "template": hit["_source"]["template"]
            })
            evaluation["runtime"]["strategies"][hit["_id"]] = {
                "_version": hit["_version"],
                "name": hit["_source"]["name"],
                "params": hit["_source"]["params"],
                "tags": hit["_source"]["tags"],
                "template": hit["_source"]["template"]
            }
        
        # Get judgements, add them to "ratings" in _rank_eval, and track their
        # original contents. Track which scenarios had judgements, in case the
        # request includes scenarios that have no judgements.
        # 
        # TODO: Implement random sampling for judgements, because there could be
        # more than 10,000 judgements per scenario.
        body = {
            "query": { "terms": { "scenario_id": evaluation["scenario_id"] }},
            "size": size,
            "version": True
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
            evaluation["runtime"]["judgements"][hit["_id"]] = {
                "_version": hit["_version"],
                "@timestamp": hit["_source"]["@timestamp"],
                "@author": hit["_source"]["@author"],
                "scenario_id": hit["_source"]["scenario_id"],
                "index": hit["_source"]["index"],
                "doc_id": hit["_source"]["doc_id"],
                "rating": hit["_source"]["rating"]
            }
        
        # Track results by strategy and scenarios
        _results = {}
        for strategy_id in evaluation["strategy_id"]:
            _results[strategy_id] = {}
            for scenario_id in evaluation["scenario_id"]:
                _results[strategy_id][scenario_id] = {
                    "metrics": {},
                    "hits": []
                }
        
        # Get scenarios
        scenarios = {}
        body = {
            "query": { "ids": { "values": evaluation["scenario_id"] }},
            "size": size,
            "version": True
        }
        es_response = es("studio").search(
            index="esrs-scenarios",
            body=body
        )
        for hit in es_response.body["hits"]["hits"]:
            scenarios[hit["_id"]] = hit["_source"]["values"]
            evaluation["runtime"]["scenarios"][hit["_id"]] = {
                "_version": hit["_version"],
                "name": hit["_source"]["name"],
                "params": hit["_source"]["params"],
                "values": hit["_source"]["values"],
                "tags": hit["_source"]["tags"]
            }
            
        # Store index relevance fingerprints
        evaluation["runtime"]["indices"] = content.make_index_relevance_fingerprints(index_pattern)
        
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
            #"mrr": {
            #    "name": "mean_reciprocal_rank",
            #    "config": {
            #        "k":  evaluation["task"]["k"]
            #    }
            #},
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
        
        # Create a set of requests for each evaluation metric
        for m in evaluation["task"]["metrics"]:
            
            # Reset the metric and requests for this iterartion
            _rank_eval["metric"] = {}
            _rank_eval["requests"] = []
            
            # Define the metric for this iteration
            metric_name = metrics_config[m]["name"]
            _rank_eval["metric"][metric_name] = metrics_config[m]["config"]
            
            # Define requests for each combination of strategies and scenarios
            grid = list(itertools.product(evaluation["strategy_id"], evaluation["scenario_id"]))
            for strategy_id, scenario_id in grid:
                _rank_eval["requests"].append({
                    "id": f"{strategy_id}~{scenario_id}",
                    "template_id": strategy_id,
                    "params": scenarios[scenario_id],
                    "ratings": ratings[scenario_id]
                })
                
            # Run _rank_eval on the content deployment and accumulate the results
            body = {
                "metric": _rank_eval["metric"],
                "requests": _rank_eval["requests"],
                "templates": _rank_eval["templates"]
            }
            es_response = es("content").rank_eval(
                index=index_pattern,
                body=body
            )
            
            # Store results
            for request_id, details in es_response.body["details"].items():
                strategy_id, scenario_id = request_id.split("~", 1)
                _results[strategy_id][scenario_id]["metrics"][m] = details["metric_score"]
                if not len(_results[strategy_id][scenario_id]["hits"]):
                    _results[strategy_id][scenario_id]["hits"] = details["hits"]
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
            
        # Restructure results for response
        evaluation["results"] = []
        for strategy_id, _strategy_results in _results.items():
            strategy_results = {
                "strategy_id": strategy_id,
                "searches": []
            }
            for scenario_id, _scenario_results in _strategy_results.items():
                scenario_results = {
                    "scenario_id": scenario_id,
                    "metrics": _scenario_results["metrics"],
                    "hits": _scenario_results["hits"]
                }
                strategy_results["searches"].append(scenario_results)
            evaluation["results"].append(strategy_results)
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
        
        # Create final response
        stopped_at = time.time()
        evaluation["@meta"]["stopped_at"] = utils.timestamp(stopped_at)
        evaluation["@meta"]["status"] = "completed"
        evaluation["took"] = int(( stopped_at - started_at) * 1000)
        
        # Store results
        if store_results:
            es_response = es("studio").update(
                index="esrs-evaluations",
                id=evaluation_id,
                doc=evaluation,
                refresh=True
            )
        return evaluation
    
    # Mark evaluation as "failed" on exception
    except Exception as e:
        if store_results:
            stopped_at = time.time()
            evaluation["@meta"]["status"] = "failed"
            evaluation["@meta"]["stopped_at"] = utils.timestamp(time.time())
            evaluation["took"] = int(( stopped_at - started_at) * 1000)
            es("studio").update(
                index="esrs-evaluations",
                id=evaluation_id,
                doc=evaluation,
                refresh=True
            )
        raise e

def browse(project_id: str, benchmark_id: str, size: int = 10000) -> Dict[str, Any]:
    """
    List evaluations in Elasticsearch.
    """
    body={
        "query": {
            "bool": {
                "filter": [
                    { "term": { "project_id": project_id }},
                    { "term": { "benchmark_id": benchmark_id }}
                ]
            }
        },
        "size": size
    }
    es_response = es("studio").search(
        index=INDEX_NAME,
        body=body,
        ignore_unavailable=True
    )
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get an evaluation in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id
    )
    return es_response

def create(
        project_id: str,
        benchmark_id: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
    """
    Create a pending evaluation in Elasticsearch.
    """
    
    # Parse task
    metrics = task.get("metrics") or [ "ndcg", "precision", "recall" ]
    k = task.get("k")
    strategies_ids = task.get("strategies", {}).get("_ids", [])
    strategies_tags = task.get("strategies", {}).get("tags", [])
    scenarios_ids = task.get("scenarios", {}).get("_ids", [])
    scenarios_tags = task.get("scenarios", {}).get("tags", [])
    scenarios_sample_size = task.get("scenarios", {}).get("sample_size") or 1000
    scenarios_sample_seed = task.get("scenarios", {}).get("sample_seed")
    
    # Valdiate task
    validate_metrics(metrics)
    validate_k(k)
        
    # Create evaluation
    doc = {
        "@meta": {
            "status": "pending",
            "created_at": utils.timestamp(),
            "started_at": None,
            "stopped_at": None
        },
        "project_id": project_id,
        "benchmark_id": benchmark_id,
        "task": {
            "metrics": metrics,
            "k": k,
            "strategies": {},
            "scenarios": {}
        }
    }
    if strategies_ids:
        doc["task"]["strategies"]["_ids"] = strategies_ids
    if strategies_tags:
        doc["task"]["strategies"]["tags"] = strategies_tags
    if scenarios_ids:
        doc["task"]["scenarios"]["_ids"] = scenarios_ids
    if scenarios_tags:
        doc["task"]["scenarios"]["tags"] = scenarios_tags
    if scenarios_sample_size:
        doc["task"]["scenarios"]["sample_size"] = scenarios_sample_size
    if scenarios_sample_seed:
        doc["task"]["scenarios"]["sample_seed"] = scenarios_sample_seed
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id(),
        document=doc,
        refresh=True
    )
    return es_response

def delete(_id: str) -> Dict[str, Any]:
    """
    Delete an evaluation in Elasticsearch.
    """
    es_response = es("studio").delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True
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
    es_response = es("studio").options(ignore_status=404).delete_by_query(
        index=INDEX_NAME,
        body=body,
        refresh=True
    )
    return es_response
    