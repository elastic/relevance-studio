# Standard packages
from typing import Any, Dict

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