# Standard packages
from copy import deepcopy
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import ProjectModel

INDEX_NAME = "esrs-projects"

def search(
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """
    Search projects in Elasticsearch.
    """
    response = utils.search_assets(
        "projects", None, text, filters, sort, size, page,
        counts=[ "displays", "scenarios", "judgements", "strategies", "benchmarks" ] if aggs else []
    )
    return response

def tags() -> Dict[str, Any]:
    """
    Search tags for projects in Elasticsearch.
    """
    es_response = utils.search_tags("projects")
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a project by in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: dict, _id: str = None) -> Dict[str, Any]:
    """
    Create a project in Elasticsearch. Allow a predetermined _id.
    """
    
    # Create, validate, and dump model
    doc = (
        ProjectModel
        .model_validate(doc)
        .model_dump(by_alias=True, exclude_unset=True)
    )

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("projects", doc)
    
    # Submit 
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: dict) -> Dict[str, Any]:
    """
    Update a project in Elasticsearch.
    """
    
    # Create, validate, and dump model
    doc_partial = (
        ProjectModel
        .model_validate(doc_partial, context={"is_partial": True})
        .model_dump(by_alias=True, exclude_unset=True)
    )
    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("projects", doc_partial)
    
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
    )
    return es_response