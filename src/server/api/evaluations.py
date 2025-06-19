# Standard packages
import itertools
import time
from typing import Any, Dict

# App packages
from . import content
from .. import utils
from ..client import es

INDEX_NAME = "esrs-evaluations"

def run(task: Dict[str, Any]):
    """
    Expected structure of the request payload:
    
    {
        "strategies": [
            STRATEGY_ID,
            ...
        ],
        "scenarios": [
            SCENARIO_ID,
            ...
        ],
        "metrics": [
            METRIC_NAME,
            ...
        ],
        "k": INTEGER
    }
    
    Example:
    
    {
        "strategies": [
            "classical-name-match",
            "classical-name-match-fuzzy",
            "classical-multifield-match",
            "classical-multifield-match-boosts",
            "classical-multifield-match-signals-boosts",
            "elser-name-match",
            "elser-multifield-match",
            "elser-multifield-match-boosts",
            "elser-multifield-match-signals-boosts"
        ],
        "scenarios": [
            "cae18e7a-a4be-495f-a13b-69fdc1463ccb"
        ],
        "metrics": [
            "ndcg",
            "precision",
            "recall"
        ],
        "k": 10
    }
    
    Structure of the response payload:
    
    {
        "@timestamp": DATE,
        "project_id": KEYWORD,
        "strategy_id": [ KEYWORD, ... ],
        "scenario_id": [ KEYWORD, ... ],
        "config": {
            "metrics": [ KEYWORD, ... ],
            "k": INTEGER
        },
        "results": [
            {
                "strategy_id": KEYWORD,
                "searches": [
                    {
                        "scenario_id": KEYWORD,
                        "metrics": {
                            "ndcg": FLOAT,
                            "precision": FLOAT,
                            "recall": FLOAT
                        },
                        "hits": [
                            {
                                "hit": {
                                    "_id": KEYWORD,
                                    "_index": KEYWORD,
                                    "_score": FLOAT
                                },
                                "rating": INTEGER
                            }
                        ]
                    }
                ]
            }
        ],
        "runtime": {
            "indices": {
                INDEX_NAME: {
                    "fingerprint": KEYWORD,
                    "shards": [
                        {
                            "id": KEYWORD,
                            "max_seq_no": KEYWORD
                        },
                        ...
                    ],
                    "uuid": KEYWORD
                },
                ...
            },
            "strategies": {
                STRATEGY_ID: {
                    "name": KEYWORD,
                    "params": [ KEYWORD, ...],
                    "tags": [ KEYWORD, ...],
                    "template": OBJECT,
                },
                ...
            },
            "scenarios": {
                SCENARIO_ID: {
                    "name": KEYWORD,
                    "params": [ KEYWORD, ...],
                    "tags": [ KEYWORD, ...],
                },
                ...
            }
        },
        "unrated_docs": [
            {
                "_id": KEYWORD,
                "_index": KEYWORD
            },
            ...
        ],
        "took": INTEGER
    }
    """
    
    # Start timer
    start_time = time.time()
    
    # Parse and validate request
    project_id = task["project_id"]
    task["store_results"] = task.get("store_results")
    task["k"] = int(task.get("k")) or 10
    task["metrics"] = task.get("metrics") or [ "ndcg", "precision", "recall" ]
    metrics_config = {
        # TODO: Support other types of metrics (commented out below)
        #"dcg": {
        #    "name": "dcg",
        #    "config": {
        #        "k": task["k"]
        #    }
        #},
        #"err": {
        #    "name": "expected_reciprocal_rank",
        #    "config": {
        #        "k": k,
        #        "maximum_relevance": rating_scale_max
        #    }
        #},
        #"mrr": {
        #    "name": "mean_reciprocal_rank",
        #    "config": {
        #        "k": task["k"]
        #    }
        #},
        "ndcg": {
            "name": "dcg",
            "config": {
                "k": task["k"],
                "normalize": True
            }
        },
        "precision": {
            "name": "precision",
            "config": {
                "k": task["k"],
                "ignore_unlabeled": False
            }
        },
        "recall": {
            "name": "recall",
            "config": {
                "k": task["k"]
            }
        }
    }
    valid_metrics = metrics_config.keys()
    if not set(task["metrics"]).issubset(set(valid_metrics)):
        raise Exception(f"\"metrics\" only supports these values: {', '.join(sorted(valid_metrics))}")
    if not task["k"] > 0:
        raise Exception("\"k\" must be greater than 0.")
    if not task.get("strategies"):
        raise Exception("\"strategies\" must have one or more strategy_id values.")
    if not task.get("scenarios"):
        raise Exception("\"scenarios\" must have one or more scenario_id values.")
    if task["store_results"] in ( "", None ):
        task["store_results"] = True
    elif str(task["store_results"]).lower() in ( "true", "false" ):
        task["store_results"] = True if task["store_results"].lower() == "true" else False
    else:
        raise Exception("\"store_results\" must be true or false (or not given).")
    
    # Prepare _rank_eval request
    _rank_eval = {
        "templates": [],
        "requests": [],
        "metric": {}
    }
    
    # Store the contents of the assets used at runtime in this evaluation
    runtime_indices = {}
    runtime_strategies = {}
    runtime_scenarios = {}
    runtime_judgements = {}
    
    # Set a default size of 10,000 hits per request when retrieving
    # strategies, scenarios, or judgements
    size = 10000
    
    # Get project
    es_response = es("studio").get(index="esrs-projects", id=project_id)
    index_pattern = es_response.body["_source"]["index_pattern"]
    rating_scale_max = es_response.body["_source"]["rating_scale"]["max"]
    
    # Get strategies and convert them to templates in _rank_eval
    body = {
        "query": { "ids": { "values": task["strategies"] }},
        "size": size,
        "version": True
    }
    es_response = es("studio").options(ignore_status=404).search(index="esrs-strategies", body=body)
    for hit in es_response.body["hits"]["hits"]:
        _rank_eval["templates"].append({
            "id": hit["_id"],
            "template": hit["_source"]["template"]
        })
        runtime_strategies[hit["_id"]] = {
            "_version": hit["_version"],
            "name": hit["_source"]["name"],
            "params": hit["_source"]["params"],
            "tags": hit["_source"]["tags"],
            "template": hit["_source"]["template"]
        }
    
    # Get judgements and convert them to ratings in _rank_eval.
    # Keep track of which scenarios had judgements, in case the request
    # includes scenarios that have no judgements.
    scenarios_with_judgements = set()
    body = {
        "query": { "terms": { "scenario_id": task["scenarios"] }},
        "size": size,
        "version": True
    }
    es_response = es("studio").options(ignore_status=404).search(index="esrs-judgements", body=body)
    ratings = {}
    for hit in es_response.body["hits"]["hits"]:
        scenario_id = hit["_source"]["scenario_id"]
        scenarios_with_judgements.add(scenario_id)
        if scenario_id not in ratings:
            ratings[scenario_id] = []
        ratings[scenario_id].append({
            "_index": hit["_source"]["index"],
            "_id": hit["_source"]["doc_id"],
            "rating": hit["_source"]["rating"],
        })
        runtime_judgements[hit["_id"]] = {
            "_version": hit["_version"],
            "@timestamp": hit["_source"]["@timestamp"],
            "@author": hit["_source"]["@author"],
            "scenario_id": hit["_source"]["scenario_id"],
            "index": hit["_source"]["index"],
            "doc_id": hit["_source"]["doc_id"],
            "rating": hit["_source"]["rating"]
        }
    scenarios_with_judgements = list(scenarios_with_judgements)
    
    # Store results by strategy and scenarios
    _results = {}
    for strategy_id in task["strategies"]:
        _results[strategy_id] = {}
        for scenario_id in scenarios_with_judgements:
            _results[strategy_id][scenario_id] = {
                "metrics": {},
                "hits": []
            }
    
    # Get scenarios
    scenarios = {}
    body = {
        "query": { "ids": { "values": scenarios_with_judgements }},
        "size": size,
        "version": True
    }
    es_response = es("studio").options(ignore_status=404).search(index="esrs-scenarios", body=body)
    for hit in es_response.body["hits"]["hits"]:
        scenarios[hit["_id"]] = hit["_source"]["values"]
        runtime_scenarios[hit["_id"]] = {
            "_version": hit["_version"],
            "name": hit["_source"]["name"],
            "values": hit["_source"]["params"],
            "values": hit["_source"]["values"],
            "tags": hit["_source"]["tags"]
        }
        
    # Store index relevance fingerprints
    runtime_indices = content.make_index_relevance_fingerprints(index_pattern)
    
    # Store any unrated docs found in the evaluation
    _unrated_docs = {}
    
    # Create a set of requests for each evaluation metric
    for m in task["metrics"]:
        
        # Reset the metric and requests for this iterartion
        _rank_eval["metric"] = {}
        _rank_eval["requests"] = []
        
        # Define the metric for this iteration
        metric_name = metrics_config[m]["name"]
        _rank_eval["metric"][metric_name] = metrics_config[m]["config"]
        
        # Define requests for each combination of strategies and scenarios
        grid = list(itertools.product(task["strategies"], scenarios_with_judgements))
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
    results = []
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
        results.append(strategy_results)
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
    unrated_docs = sorted(unrated_docs, key=lambda doc: doc["count"], reverse=True)
    
    # Create final response
    response = {
        "@timestamp": utils.timestamp(start_time),
        "project_id": project_id,
        "strategy_id": task["strategies"],
        "scenario_id": scenarios_with_judgements,
        "config": {
            "metrics": task["metrics"],
            "k": task["k"]
        },
        "results": results,
        "runtime": {
            "indices": runtime_indices,
            "strategies": runtime_strategies,
            "scenarios": runtime_scenarios,
            "judgements": runtime_judgements
        },
        "unrated_docs": unrated_docs
    }
    response["took"] = int((time.time() - start_time) * 1000)
    
    # Store results
    if task["store_results"]:
        es_response = es("studio").index(
            index="esrs-evaluations",
            id=utils.unique_id(),
            document=response,
            refresh=True
        )
        response["_id"] = es_response["_id"]
    return response

def browse(project_id: str, size: int = 10000) -> Dict[str, Any]:
    """
    List evaluations in Elasticsearch.
    """
    body={
        "query": {
            "bool": {
                "filter": {
                    "term": {
                        "project_id": project_id
                    }
                }
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