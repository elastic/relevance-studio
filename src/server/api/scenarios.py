# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es

INDEX_NAME = "esrs-scenarios"

def browse(project_id: str, size: int = 10000) -> Dict[str, Any]:
    """
    List scenario in Elasticsearch.
    """
    body = {
        "size": 10000,
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
                "_index": "esrs-scenarios"
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
                                "_index": "esrs-judgements"
                            }
                        }
                    }
                }
            }
        }
    }
    index = ",".join([
        "esrs-scenarios",
        "esrs-judgements"
    ])
    response = es("studio").search(
        index=index,
        body=body,
        ignore_unavailable=True
    )
    return response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a scenario in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id
    )
    return es_response

def create(
        project_id: str,
        name: str,
        values: Dict[str, Any],
        tags: List[str] = [],
    ) -> Dict[str, Any]:
    """
    Create a scenario in Elasticsearch.
    
    Use a deterministic _id for UX efficiency, and to prevent the creation of
    duplicate scenarios for the same values.
    """
    doc = {
        "@timestamp": utils.timestamp(),
        "project_id": project_id,
        "name": name,
        "tags": tags or [],
        "params": list(values.keys()),
        "values": values,
    }
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id([ project_id, values ]),
        document=doc,
        refresh=True
    )
    return es_response

def update(
        _id: str,
        name: str = None,
        tags: List[str] = [],
    ) -> Dict[str, Any]:
    """
    Update a scenario in Elasticsearch.
    """
    doc_updates = {
        "@timestamp": utils.timestamp()
    }
    if name:
        doc_updates["name"] = name
    if tags:
        doc_updates["tags"] = tags
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_updates,
        refresh=True
    )
    return es_response

def delete(_id: str) -> Dict[str, Any]:
    """
    Delete a scenario in Elasticsearch.
    Delete all judgements that share its scenario_id.
    """
    body = {
        "query": {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-scenarios" }},
                                { "term": { "_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-judgements" }},
                                { "term": { "scenario_id": _id }}
                            ]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
    es_response = es("studio").delete_by_query(
        index="esrs-scenarios,esrs-judgements",
        body=body,
        refresh=True,
        conflicts="proceed",
        ignore_unavailable=True
    )
    return es_response