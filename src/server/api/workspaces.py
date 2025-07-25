# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import WorkspaceCreate, WorkspaceUpdate

INDEX_NAME = "esrs-workspaces"

def search(
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        aggs: bool = False,
    ) -> Dict[str, Any]:
    """
    Search for workspaces.
    """
    response = utils.search_assets(
        "workspaces", None, text, filters, sort, size, page,
        counts=[ "displays", "scenarios", "judgements", "strategies", "benchmarks" ] if aggs else []
    )
    return response

def tags() -> Dict[str, Any]:
    """
    List all workspace tags (up to 10,000).
    """
    es_response = utils.search_tags("workspaces")
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a workspace by its _id.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: Dict[str, Any], _id: str = None, user: str = None) -> Dict[str, Any]:
    """
    Create a workspace.
    
    Accepts an optional pregenerated _id for idempotence.
    """
    
    # Create, validate, and dump model
    doc = WorkspaceCreate.model_validate(doc, context={"user": user}).serialize()

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("workspaces", doc)
    
    # Submit 
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any], user: str = None) -> Dict[str, Any]:
    """
    Update a workspace by its _id.
    """
    
    # Create, validate, and dump model
    doc_partial = WorkspaceUpdate.model_validate(doc_partial, context={"user": user}).serialize()
    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("workspaces", doc_partial)
    
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
    Delete a workspace by its _id.
    
    This also deletes all displays, scenarios, judgements, strategies,
    benchmarks, and evaluations that share its workspace_id.
    """
    body = {
        "query": {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-workspaces" }},
                                { "term": { "_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-displays" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-scenarios" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-judgements" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-strategies" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-benchmarks" }},
                                { "term": { "workspace_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "_index": "esrs-evaluations" }},
                                { "term": { "workspace_id": _id }}
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
            "esrs-workspaces",
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