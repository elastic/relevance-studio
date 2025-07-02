# Standard packages
from typing import Any, Dict

# App packages
from .. import utils
from ..client import es
from ..models import JudgementModel

INDEX_NAME = "esrs-judgements"
SEARCH_FIELDS = utils.get_search_fields_from_mapping("judgements")

def search(
        project_id: str,
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
                    { "term": { "project_id": project_id }},
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
        body["query"]["bool"]["filter"].append({
            "term": { "@author": "human"}
        })
    elif filter == "rated-ai":
        body["query"]["bool"]["filter"].append({
            "term": { "@author": "ai"}
        })
    if sort == "rating-newest":
        body["sort"] = [{
            "@timestamp": "desc"
        }]
    elif sort == "rating-oldest":
        body["sort"] = [{
            "@timestamp": "asc"
        }]
    es_response = es("studio").search(index="esrs-judgements", body=body)
    for hit in es_response.body.get("hits", {}).get("hits") or []:
        _index = hit["_source"]["index"]
        _id = hit["_source"]["doc_id"]
        if _index not in judgements:
            judgements[_index] = {}
        judgements[_index][_id] = {
            "_id": hit["_id"],
            "@timestamp": hit["_source"].get("@timestamp"),
            "@author": hit["_source"].get("@author"),
            "rating": hit["_source"].get("rating")
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
            "_id": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("_id", None),
            "@timestamp": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("@timestamp", None),
            "@author": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("@author", None),
            "rating": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("rating", None),
            "doc": hit
        }
    if response["hits"]["hits"] and sort in ( "rating-newest", "rating-oldest" ):
        reverse = True if sort == "rating-newest" else False
        fallback = "0000-01-01T00:00:00Z" if not reverse else "9999-12-31T23:59:59Z"
        response["hits"]["hits"] = sorted(response["hits"]["hits"], key=lambda hit: hit.get("@timestamp") or fallback, reverse=reverse)
    return response

def set(doc: JudgementModel) -> Dict[str, Any]:
    """
    Create or update a judgement in Elasticsearch.
    
    Use a deterministic _id for UX efficiency, and to prevent the creation of
    duplicate judgements for the same scenario, index, and doc.
    """
    # Always use the latest timestamp
    doc = doc.model_copy(update={"timestamp_": utils.timestamp()})
    # Copy searchable fields to _search
    doc_dict = doc.model_dump(by_alias=True, exclude_unset=True)
    doc_dict = utils.copy_fields_to_search(doc_dict, SEARCH_FIELDS)
    doc_dict = utils.remove_empty_values(doc_dict)
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id([
            doc.project_id,
            doc.scenario_id,
            doc.index,
            doc.doc_id
        ]),
        document=doc_dict,
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