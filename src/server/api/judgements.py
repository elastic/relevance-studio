# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

# Standard packages
from typing import Any, Dict

# App packages
from .. import utils
from ..client import es
from ..models import JudgementCreate

INDEX_NAME = "esrs-judgements"
SEARCH_FIELDS = utils.get_search_fields_from_mapping("judgements")

def search(
        workspace_id: str,
        scenario_id: str,
        index_pattern: str,
        query: Dict[str, Any] = {},
        query_string: str = "*",
        filter: str = None, # options: "rated", "rated-ai", "rated-human", "unrated" (or omitted for no filter)
        sort: str = None, # options: "match", "rating-newest", "rating-oldest"
        _source: Dict[str, Any] = None
    ) -> Dict[str, Any]:
    """
    Get documents from the content deployment with ratings joined to them.
    """
    response = {}
        
    # Get judgements for scenario
    judgements = {}
    body = {
        "size": 10000,
        "query": {
            "bool": {
                "filter": [
                    { "term": { "workspace_id": workspace_id }},
                    { "term": { "scenario_id": scenario_id }}
                ]
            }
        },
        "_source": {
            "excludes": [
                "_search"
            ]
        }
    }
    if filter == "rated-human":
        body["query"]["bool"]["must_not"] = {
            "term": { "@meta.created_by": "ai"}
        }
    elif filter == "rated-ai":
        body["query"]["bool"]["filter"].append({
            "term": { "@meta.created_by": "ai"}
        })
    if sort == "rating-newest":
        body["sort"] = [{
            "@meta.created_at": "desc"
        }]
    elif sort == "rating-oldest":
        body["sort"] = [{
            "@meta.created_at": "asc"
        }]
    es_response = es("studio").search(index="esrs-judgements", body=body)
    for hit in es_response.body.get("hits", {}).get("hits") or []:
        _index = hit["_source"]["index"]
        _id = hit["_source"]["doc_id"]
        if _index not in judgements:
            judgements[_index] = {}
        judgements[_index][_id] = {
            "_id": hit["_id"],
            "@meta": hit["_source"].get("@meta"),
            "rating": hit["_source"].get("rating"),
        }
        
    # Search docs on the content deployment
    # Exclude fields that exist only for searchability
    body["_source"] = { "excludes": [ "_search" ]}
    if _source:
        if _source.get("includes"):
            body["_source"]["includes"] = _source["includes"]
        if _source.get("excludes"):
            for field in _source["excludes"]:
                body["_source"]["excludes"].append(field)
    body = {
        "size": 48,
        "_source": _source
    }
    if query:
        # From strategy editor UI
        if "retriever" in query:
            body["retriever"] = query["retriever"]
        elif "query" in query:
            body["query"] = query["query"]
        elif "knn" in query:
            body["knn"] = query["knn"]
        else:
            raise Exception("Unsupported query syntax")
    else:
        # From judgements search UI
        body["query"] = {
            "bool": {
                "must": {
                    "query_string": {
                        "query": query_string or "*",
                        "default_operator": "AND"
                    }
                }
            }
        }
    
    # Filter docs by judgements (used judgement search UI)
    if filter and filter != "all":
        filter_clauses = []
        for _index in judgements.keys():
            filter_clauses.append({
                "bool": {
                    "filter": [
                        { "term": { "_index": _index }},
                        { "ids": { "values": list(judgements[_index].keys()) }}
                    ]
                }
            })
        if filter == "unrated":
            body["query"]["bool"]["must_not"] = filter_clauses
        else:
            body["query"]["bool"]["should"] = filter_clauses
            body["query"]["bool"]["minimum_should_match"] = 1
    if sort == "match":
        body["sort"] = [{
            "_score": "desc"
        }]
    es_response = es("content").search(index=index_pattern, body=body)
    
    # Merge docs and ratings
    response["hits"] = es_response.body["hits"]
    for i, hit in enumerate(response["hits"]["hits"]):
        response["hits"]["hits"][i] = {
            "_id": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("_id"),
            "@meta": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("@meta"),
            "rating": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("rating"),
            "doc": hit
        }
    if response["hits"]["hits"] and sort in ( "rating-newest", "rating-oldest" ):
        reverse = True if sort == "rating-newest" else False
        fallback = "0000-01-01T00:00:00Z" if not reverse else "9999-12-31T23:59:59Z"
        response["hits"]["hits"] = sorted(response["hits"]["hits"], key=lambda hit: hit.get("@meta", {}).get("created_at") or fallback, reverse=reverse)
    return response

def set(doc: Dict[str, Any], user: str = None) -> Dict[str, Any]:
    """
    Create or update a judgement.
    
    Gemerates a deterministic _id for UX efficiency, and to prevent the creation
    of duplicate judgements for the same combination of scenario, index, and doc.
    """
    
    # Create, validate, and dump model
    doc = JudgementCreate.model_validate(doc, context={"user": user}).serialize()
    print(doc)

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("judgements", doc)
    
    # Submit
    script = {
        "scripted_upsert": True,
        "script": {
            "source": """
                if (ctx.op == 'create') {
                    ctx._source.rating = params.rating;
                    ctx._source['@meta'] = [
                        'created_at': params.now,
                        'created_by': params.username,
                        'updated_at': null,
                        'updated_by': null
                    ];
                } else {
                    ctx._source.rating = params.rating;
                    ctx._source['@meta'].updated_at = params.now;
                    ctx._source['@meta'].updated_by = params.username;
                }
            """,
            "lang": "painless",
            "params": {
                "rating": doc["rating"],
                "now": doc["@meta"]["created_at"],
                "username": doc["@meta"]["created_by"]
            }
        },
        "upsert": doc
    }

    es_response = es("studio").update(
        index=INDEX_NAME,
        id=utils.unique_id([
            doc["workspace_id"],
            doc["scenario_id"],
            doc["index"],
            doc["doc_id"],
        ]),
        body=script,
        refresh=True
    )
    return es_response

def unset(_id: str) -> Dict[str, Any]:
    """
    Delete a judgement in Elasticsearch.
    """
    es_response = es("studio").delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True
    )
    return es_response