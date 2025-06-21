# Standard packages
import random
from typing import Any, Dict, List, Set, Tuple

# App packages
from .. import utils
from ..client import es

INDEX_NAME = "esrs-benchmarks"

def browse(project_id: str, size: int = 10000) -> Dict[str, Any]:
    """
    List benchmarks in Elasticsearch.
    """
    body = {
        "size": size,
        "query": {
            "bool": {
                "filter": {
                    "term": {
                        "project_id": project_id
                    }
                }
            }
        },
        "post_filter": {
            "term": {
                "_index": "esrs-benchmarks"
            }
        },
        "aggs": {
            "counts": {
                "terms": {
                    "field": "scenario_id",
                    "size": 10000
                },
                "aggs": {
                    "judgements": {
                        "filter": {
                            "term": {
                                "_index": "esrs-evaluations"
                            }
                        }
                    }
                }
            }
        }
    }
    index = ",".join([
        "esrs-benchmarks",
        "esrs-evaluations"
    ])
    es_response = es("studio").search(
        index=index,
        body=body,
        ignore_unavailable=True
    )
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a benchmark in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id
    )
    return es_response

def create(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a benchmark in Elasticsearch.
    """
    doc.pop("_id", None) # es doesn't want _id in doc
    es_response = es("studio").index(
        index="esrs-benchmarks",
        id=utils.unique_id(),
        document=doc,
        refresh=True
    )
    return es_response

def update(_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a benchmark in Elasticsearch.
    """
    doc.pop("_id", None) # es doesn't want _id in doc
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc,
        refresh=True
    )
    return es_response

def delete(_id: str) -> Dict[str, Any]:
    """
    Delete a benchmark in Elasticsearch.
    Delete all evaluations that share its scenario_id.
    """
    body = {
        "query": {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-benchmarks" }},
                                { "term": { "_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-evaluations" }},
                                { "term": { "benchmark_id": _id }}
                            ]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
    es_response = es("studio").delete_by_query(
        index="esrs-benchmarks,esrs-evaluations",
        body=body,
        refresh=True,
        conflicts="proceed",
        ignore_unavailable=True
    )
    return es_response

def make_candidate_pool(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    match_mode = payload.get("match_mode", "subset")
    sample_size = min(int(payload.get("scenario_sample_size", 1000)), 1000)
    assert match_mode in {"exact", "subset"}

    def fetch_strategies() -> Dict[str, Set[str]]:
        """
        Strategies can be optionally filtered by _ids or strategy tags.
        """
        _ids = payload.get("strategies", {}).get("_ids", [])
        tags = payload.get("strategies", {}).get("tags", [])
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "project_id": project_id }},
                        { "exists": { "field": "params" }}
                    ]
                }
            },
            "size": 10000,
            "_source": [ "params" ]
        }
        if _ids:
            body["query"]["bool"]["filter"].append({ "terms": { "_id": _ids }})
        elif tags:
            body["query"]["bool"]["filter"].append({ "terms": { "tags": tags }})
        response = es("studio").options(ignore_status=404).search(
            index="esrs-strategies",
            body=body
        )
        strategies = {}
        for hit in response["hits"]["hits"]:
            hit_id = hit["_id"]
            params = set(hit["_source"]["params"])
            strategies[hit_id] = params
        return strategies

    def fetch_runnable_scenarios() -> Dict[str, Tuple[Set[str], List[str], float]]:
        _ids = payload.get("scenarios", {}).get("_ids", [])
        tags = payload.get("scenarios", {}).get("tags", [])
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "project_id": project_id }},
                        { "exists": { "field": "params" }}
                    ]
                }
            },
            "size": 10000,
            "_source": [ "params", "tags" ]
        }
        if _ids:
            body["query"]["bool"]["filter"].append({ "terms": { "_id": _ids }})
        elif tags:
            body["query"]["bool"]["filter"].append({ "terms": { "tags": tags }})

        response = es("studio").options(ignore_status=404).search(
            index="esrs-scenarios",
            body=body
        )
        scenarios = {}
        for hit in response["hits"]["hits"]:
            hit_id = hit["_id"]
            params = set(hit["_source"]["params"])
            tags = hit["_source"].get("tags", [])
            scenarios[hit_id] = (params, tags)

        # Fetch average rating per scenario
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "project_id": project_id }},
                        { "terms": { "scenario_id": list(scenarios.keys()) }},
                        { "range": { "rating": { "gt": 0 }}}
                    ]
                }
            },
            "aggs": {
                "by_scenario": {
                    "terms": {
                        "field": "scenario_id",
                        "size": 10000
                    },
                    "aggs": {
                        "avg_rating": { "avg": { "field": "rating" }}
                    }
                }
            },
            "size": 0,
            "_source": False
        }
        response = es("studio").search(
            index="esrs-judgements",
            body=body
        )
        ratings = {}
        for bucket in response["aggregations"]["by_scenario"]["buckets"]:
            scenario_id = bucket["key"]
            avg_rating = bucket["avg_rating"]["value"]
            ratings[scenario_id] = avg_rating

        # Filter runnable only
        scenarios_runnable = {}
        for _id, (params, tags) in scenarios.items():
            if _id in ratings:
                scenarios_runnable[_id] = ( params, tags, ratings[_id] )
        return sample_scenarios(scenarios_runnable, sample_size)

    def sample_scenarios(scenarios: Dict[str, Tuple[Set[str], List[str], float]], n: int):
        if len(scenarios) <= n:
            return scenarios # no need to sample

        # Build buckets by (tag, rating_bin)
        buckets = {}
        for sid, (params, tags, rating) in scenarios.items():
            rating_bin = int(rating) # crude bucketing
            for tag in tags or ["_no_tag"]:
                key = (tag, rating_bin)
                buckets.setdefault(key, []).append((sid, params, tags, rating))

        selected = {}
        bucket_keys = list(buckets.keys())
        while len(selected) < n and bucket_keys:
            seed = payload.get("seed", random.randrange(1 << 30)) # deterministic if seed is given, else random every time
            random.Random(seed).shuffle(bucket_keys)
            for key in bucket_keys:
                if buckets[key]:
                    sid, params, tags, rating = buckets[key].pop()
                    selected[sid] = (params, tags, rating)
                    if len(selected) >= n:
                        break
            bucket_keys = [ k for k in bucket_keys if buckets[k] ] # drop empty buckets
        return selected
    
    # Fetch strategies and runnable scenarios
    strategies = fetch_strategies()
    scenarios = fetch_runnable_scenarios()

    # Filter strategies and scenarios by their compatibility
    if match_mode == "exact":
        # Strategy params and scenario params must match exactly
        compatible = []
        for strategy_id, strategy_params in strategies.items():
            for scenario_id, ( scenario_params, _, _ ) in scenarios.items():
                if strategy_params == scenario_params:
                    compatible.append(( strategy_id, scenario_id ))
    else:
        # Strategy params must all be present in scenario params
        compatible = []
        for strategy_id, strategy_params in strategies.items():
            for scenario_id, ( scenario_params, _, _ ) in scenarios.items():
                if strategy_params.issubset(scenario_params):
                    compatible.append(( strategy_id, scenario_id ))
    return {
        "strategies": sorted({ scenariod_id for scenariod_id, _ in compatible }),
        "scenarios": sorted({ strategy_id for _, strategy_id in compatible })
    }