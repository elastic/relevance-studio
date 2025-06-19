# Standard packages
from typing import Any, Dict

# App packages
from .. import utils
from ..client import es

INDEX_NAME = "esrs-projects"

def browse(size: int = 10000) -> Dict[str, Any]:
    """
    List projects in Elasticsearch.
    """
    body = {
        "size": size,
        "post_filter": {
            "term": {
                "_index": "esrs-projects"
            }
        },
        "aggs": {
            "counts": {
                "terms": {
                    "field": "project_id",
                    "size": 10000
                },
                "aggs": {
                    "displays": {
                        "filter": {
                            "term": {
                                "_index": "esrs-displays"
                            }
                        }
                    },
                    "scenarios": {
                        "filter": {
                            "term": {
                                "_index": "esrs-scenarios"
                            }
                        }
                    },
                    "judgements": {
                        "filter": {
                            "term": {
                                "_index": "esrs-judgements"
                            }
                        }
                    },
                    "strategies": {
                        "filter": {
                            "term": {
                                "_index": "esrs-strategies"
                            }
                        }
                    },
                    "benchmarks": {
                        "filter": {
                            "term": {
                                "_index": "esrs-benchmarks"
                            }
                        }
                    },
                    "evaluations": {
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
        "esrs-projects",
        "esrs-displays",
        "esrs-scenarios",
        "esrs-judgements",
        "esrs-strategies",
        "esrs-benchmarks",
        "esrs-evaluations",
    ])
    es_response = es("studio").search(
        index=index,
        body=body,
        ignore_unavailable=True
    )
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a project in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id
    )
    return es_response

def create(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a project in Elasticsearch.
    """
    doc.pop("_id", None) # es doesn't want _id in doc
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id(),
        document=doc,
        refresh=True
    )
    return es_response

def update(_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a project in Elasticsearch.
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
    Delete a project in Elasticsearch.
    """
    body = {
        "query": {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-projects" }},
                                { "term": { "_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-displays" }},
                                { "term": { "project_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-scenarios" }},
                                { "term": { "project_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-judgements" }},
                                { "term": { "project_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-strategies" }},
                                { "term": { "project_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-benchmarks" }},
                                { "term": { "project_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-evaluations" }},
                                { "term": { "project_id": _id }}
                            ]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
    es_response = es("studio").delete_by_query(
        index=",".join([
            "esrs-projects",
            "esrs-displays",
            "esrs-scenarios",
            "esrs-judgements",
            "esrs-strategies",
            "esrs-benchmarks",
            "esrs-evaluations",
        ]),
        body=body,
        refresh=True,
        conflicts="proceed",
        ignore_unavailable=True
    )
    return es_response