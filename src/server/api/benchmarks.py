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
    
    # Create, validate, and dump model
    doc = (
        BenchmarkModel
        .model_validate(doc)
        .model_dump(by_alias=True, exclude_unset=True)
    )

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("benchmarks", doc)
    
    # Submit
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: BenchmarkModel) -> Dict[str, Any]:
    """
    Update a benchmark in Elasticsearch.
    """
    
    # Create, validate, and dump model
    doc_partial = (
        BenchmarkModel
        .model_validate(doc_partial, context={"is_partial": True})
        .model_dump(by_alias=True, exclude_unset=True)
    )
    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("benchmarks", doc_partial)
    
    # Submit
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_partial,
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
        conflicts="proceed"
    )
    return es_response

####  Candidate Selection  #####################################################

def fetch_strategies(
        project_id: str,
        strategy_ids: List = None,
        strategy_tags: List = None,
        strategy_ids_excluded: List = None,
    ) -> Dict[str, Set[str]]:
    """
    Strategies can be optionally filtered by _ids or tags.
    """
    strategy_ids = strategy_ids or []
    strategy_tags = strategy_tags or []
    strategy_ids_excluded = strategy_ids_excluded or []
    body = {
        "query": {
            "bool": {
                "filter": [
                    { "term": { "project_id": project_id }},
                    { "exists": { "field": "params" }} # strategies aren't runnable if they don't have params
                ]
            }
        },
        "size": 10000,
        "_source": [ "params" ]
    }
    
    # Include strategies whose _id exists in strategy_ids or strategy_tags
    should_clauses = []
    if strategy_ids:
        should_clauses.append({ "terms": { "_id": strategy_ids } })
    if strategy_tags:
        should_clauses.append({ "terms": { "tags": strategy_tags } })
    if should_clauses:
        body["query"]["bool"]["should"] = should_clauses
        body["query"]["bool"]["minimum_should_match"] = 1
        
    # Exclude strategies whose _id exists in strategy_ids_excluded
    if strategy_ids_excluded:
        body["query"]["bool"]["must_not"] = [
            { "terms": { "_id": strategy_ids_excluded } }
        ]
        
    # Fetch strategies
    response = es("studio").search(
        index="esrs-strategies",
        body=body
    )
    strategies = {}
    for hit in response["hits"]["hits"]:
        hit_id = hit["_id"]
        strategies[hit_id] = hit["_source"]
    return strategies

def sample_scenarios(
        scenarios: Dict[str, Tuple[Set[str], List[str], float]],
        sample_size: int = None,
        sample_seed: Any = None,
    ) -> Dict[str, Any]:
    
    # Determine whether sampling is applicable
    sample_size = sample_size if sample_size else 1000
    if len(scenarios) <= sample_size:
        return scenarios # no need to sample
    
    # Random sampling becomes deterministic if sample_seed is given
    sample_seed = sample_seed if sample_seed else random.randrange(1 << 30)

    # Build buckets by (tag, rating_bin)
    buckets = {}
    for sid, (params, tags, rating) in scenarios.items():
        rating_bin = int(rating) # crude bucketing
        for tag in tags or ["_no_tag"]:
            key = (tag, rating_bin)
            buckets.setdefault(key, []).append((sid, params, tags, rating))

    selected = {}
    bucket_keys = list(buckets.keys())
    while len(selected) < sample_size and bucket_keys:
        random.Random(sample_seed).shuffle(bucket_keys)
        for key in bucket_keys:
            if buckets[key]:
                sid, params, tags, rating = buckets[key].pop()
                selected[sid] = (params, tags, rating)
                if len(selected) >= sample_size:
                    break
        bucket_keys = [ k for k in bucket_keys if buckets[k] ] # drop empty buckets
    return selected

def fetch_runnable_scenarios(
        project_id: str,
        scenario_ids: List = None,
        scenario_tags: List = None,
        sample_size: int = None,
        sample_seed: int = None,
    ) -> Dict[str, Tuple[Set[str], List[str], float]]:
    """
    Scenarios can be optionally filtered by _ids or tags.
    """
    scenario_ids = scenario_ids or []
    scenario_tags = scenario_tags or []
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
    
     # Include scenarios whose _id exists in scenario_ids or scenario_tags
    should_clauses = []
    if scenario_ids:
        should_clauses.append({ "terms": { "_id": scenario_ids } })
    if scenario_tags:
        should_clauses.append({ "terms": { "tags": scenario_tags } })
    if should_clauses:
        body["query"]["bool"]["should"] = should_clauses
        body["query"]["bool"]["minimum_should_match"] = 1
        
    # Fetch scenarios
    response = es("studio").search(
        index="esrs-scenarios",
        body=body
    )
    scenarios = {}
    for hit in response["hits"]["hits"]:
        hit_id = hit["_id"]
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
    return sample_scenarios(scenarios_runnable, sample_size, sample_seed)

def make_candidate_pool(
        project_id: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
    """
    Structure of the returned object:
    
    {
        "strategies": [
            {
                "_id": STRATEGY_ID,
                "tags": [ STRATEGY_TAG, ... ],
                "_source": STRATEGY_SOURCE  // if given in task["strategies"]["docs"]
            }
        ],
        "scenarios": [
            {
                "_id": SCENARIO_ID,
                "tags": [ SCENARIO_TAG, ... ]
            },
            ...
        ]
    }
    """
    
    # Parse and validate task
    strategy_ids = task.get("strategies", {}).get("_ids") or []
    strategy_tags = task.get("strategies", {}).get("tags") or []
    strategy_docs = task.get("strategies", {}).get("docs") or []
    scenario_ids = task.get("scenarios", {}).get("_ids") or []
    scenario_tags = task.get("scenarios", {}).get("tags") or []
    scenario_sample_size = task.get("scenarios", {}).get("sample_size") or 1000
    scenario_sample_seed = task.get("scenarios", {}).get("sample_seed")
    match_mode = task.get("match_mode", "subset")
    assert match_mode in { "exact", "subset" }
    
    # Include any strategies given as docs
    strategies = {}
    strategies_docs = {}
    for doc in strategy_docs:
        assert "_id" in doc
        assert doc.get("_source", {}).get("template", {}).get("source")
        if not doc.get("params"):
            # Ensure the doc has its params defined
            # so that compatible scenarios can be selected
            doc["params"] = utils.extract_params(doc["_source"]["template"]["source"])
        strategies_docs[doc["_id"]] = doc
    for _id, doc in strategies_docs.items():
        strategies[_id] = doc
    
    # Fetch strategies
    if not strategies_docs:
        strategies_fetched = fetch_strategies(
            project_id,
            strategy_ids,
            strategy_tags,
            list(strategies), # exclude any strategies that were given as docs
        )
        strategies.update(strategies_fetched)
    
    # Fetch runnable scenarios given as _ids or tags - sampled if needed
    scenarios = fetch_runnable_scenarios(
        project_id,
        scenario_ids,
        scenario_tags,
        scenario_sample_size,
        scenario_sample_seed,
    )

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
    
    # Restructure final object
    _candidates = { "strategies": [], "scenarios": [] }
    for key in ( "strategies", "scenarios" ):
        items = candidates.get(key, {})
        for _id, tags in items.items():
            _candidate = { "_id": _id, "tags": tags }
            if key == "strategies" and _id in strategies_docs:
                _source = strategies_docs[_id]["_source"]
                if "tags" in _source:
                    _candidate["tags"] = _source["tags"]
                _candidate["_source"] = _source
            _candidates[key].append(_candidate)
    candidates = _candidates
    return candidates