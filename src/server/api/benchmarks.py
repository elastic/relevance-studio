# Standard packages
import random
from typing import Any, Dict, List, Set, Tuple

# App packages
from .. import utils
from ..client import es
from ..models import BenchmarkModel

INDEX_NAME = "esrs-benchmarks"
SEARCH_FIELDS = utils.get_search_fields_from_mapping("benchmarks")

def search(
        project_id: str,
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """
    Search benchmarks in Elasticsearch.
    """
    response = utils.search_assets(
        "benchmarks", project_id, text, filters, sort, size, page,
        counts=[ "evaluations" ] if aggs else []
    )
    return response

def tags(project_id: str) -> Dict[str, Any]:
    """
    Search tags for benchmarks in Elasticsearch.
    """
    es_response = utils.search_tags("benchmarks", project_id)
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a benchmark in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: BenchmarkModel, _id: str = None) -> Dict[str, Any]:
    """
    Create a benchmark in Elasticsearch. Allow a predetermined _id.
    """
    # Copy searchable fields to _search
    doc_dict = doc.model_dump(by_alias=True, exclude_unset=True)
    doc_dict = utils.copy_fields_to_search(doc_dict, SEARCH_FIELDS)
    doc_dict = utils.remove_empty_values(doc_dict)
    es_response = es("studio").index(
        index="esrs-benchmarks",
        id=_id or utils.unique_id(),
        document=doc_dict,
        refresh=True,
    )
    return es_response

def update(_id: str, doc: BenchmarkModel) -> Dict[str, Any]:
    """
    Update a benchmark in Elasticsearch.
    """
    # Copy searchable fields to _search
    doc_dict = doc.model_dump(by_alias=True, exclude_unset=True)
    doc_dict = utils.copy_fields_to_search(doc_dict, SEARCH_FIELDS)
    doc_dict = utils.remove_empty_values(doc_dict)
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_dict,
        refresh=True,
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
        ignore_unavailable=True,
    )
    return es_response

def make_candidate_pool(project_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    match_mode = task.get("match_mode", "subset")
    sample_size = min(int(task.get("scenarios_sample_size", 1000)), 1000)
    assert match_mode in {"exact", "subset"}

    def fetch_strategies() -> Dict[str, Set[str]]:
        """
        Strategies can be optionally filtered by _ids or strategy tags.
        """
        _ids = task.get("strategies", {}).get("_ids", [])
        tags = task.get("strategies", {}).get("tags", [])
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
            strategies[hit_id] = hit["_source"]
        return strategies

    def fetch_runnable_scenarios() -> Dict[str, Tuple[Set[str], List[str], float]]:
        _ids = task.get("scenarios", {}).get("_ids", [])
        tags = task.get("scenarios", {}).get("tags", [])
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
            scenarios[hit_id] = hit["_source"]

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
        for _id, doc in scenarios.items():
            if _id in ratings:
                scenarios_runnable[_id] = doc
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
            seed = task.get("seed", random.randrange(1 << 30)) # deterministic if seed is given, else random every time
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
    strategies = {}
    if "docs" in task.get("strategies", {}):
        for doc in task["strategies"]["docs"]:
            strategies[doc["_id"]] = doc
    else:
        strategies = fetch_strategies()
    scenarios = fetch_runnable_scenarios()

    # Filter strategies and scenarios by their compatibility
    candidates = {
        "strategies": {},
        "scenarios": {}
    }
    if match_mode == "exact":
        # Strategy params and scenario params must match exactly
        for strategy_id, strategy_doc in strategies.items():
            strategy_params = strategy_params
            for scenario_id, scenario_doc in scenarios.items():
                if strategy_doc.get("params", []) == scenario_doc.get("params", []):
                    candidates["strategies"][strategy_id] = sorted(strategy_doc.get("tags") or [])
                    candidates["scenarios"][scenario_id] = sorted(scenario_doc.get("tags") or [])
    else:
        # Strategy params must all be present in scenario params
        for strategy_id, strategy_doc in strategies.items():
            for scenario_id, scenario_doc in scenarios.items():
                if set(strategy_doc.get("params", [])).issubset(set(scenario_doc.get("params", []))):
                    candidates["strategies"][strategy_id] = sorted(strategy_doc.get("tags") or [])
                    candidates["scenarios"][scenario_id] = sorted(scenario_doc.get("tags") or [])
    return candidates