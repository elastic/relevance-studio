# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import ScenarioModel, MetaModel

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

def create(doc: ScenarioModel) -> Dict[str, Any]:
    """
    Create a scenario in Elasticsearch.
    
    Use a deterministic _id for UX efficiency, and to prevent the creation of
    duplicate scenarios for the same values.
    """

    # Add @meta.created_* fields
    doc = MetaModel.apply_meta_create(doc)
    
    # Create, validate, and dump model
    doc = (
        ScenarioModel
        .model_validate(doc)
        .model_dump(by_alias=True, exclude_unset=True)
    )

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

def update(_id: str, doc_partial: ScenarioModel) -> Dict[str, Any]:
    """
    Update a scenario in Elasticsearch.
    """
    
    # Add @meta.updated_* fields
    doc_partial = MetaModel.apply_meta_update(doc_partial)
    
    # Create, validate, and dump model
    doc_partial = (
        ScenarioModel
        .model_validate(doc_partial, context={"is_partial": True})
        .model_dump(by_alias=True, exclude_unset=True)
    )
    
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
    )
    return es_response