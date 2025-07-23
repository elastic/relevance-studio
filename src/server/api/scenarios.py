# Standard packages
from typing import Any, Dict, List, ClassVar

# App packages
from .. import utils
from ..client import es
from ..models import ScenarioCreate, ScenarioUpdate

INDEX_NAME = "esrs-scenarios"

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
    Search scenarios in Elasticsearch.
    """
    response = utils.search_assets(
        "scenarios", project_id, text, filters, sort, size, page,
        counts=[ "judgements" ] if aggs else []
    )
    return response

def tags(project_id: str) -> Dict[str, Any]:
    """
    Search tags for scenarios in Elasticsearch.
    """
    es_response = utils.search_tags("scenarios", project_id)
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a scenario in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a scenario in Elasticsearch.
    
    Use a deterministic _id for UX efficiency, and to prevent the creation of
    duplicate scenarios for the same values.
    """
    
    # Create, validate, and dump model
    doc = ScenarioCreate.model_validate(doc).serialize()

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("scenarios", doc)
    
    # Submit
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id([ doc["project_id"], doc["values"] ]),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a scenario in Elasticsearch.
    """
    
    # Create, validate, and dump model
    doc_partial = ScenarioUpdate.model_validate(doc_partial).serialize()
    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("scenarios", doc_partial)
    
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
                                { "term": { "@meta.type": "scenarios" }},
                                { "term": { "_id": _id }}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "filter": [
                                { "term": { "@meta.type": "judgements" }},
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
    )
    return es_response