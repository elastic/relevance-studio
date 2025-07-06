# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import StrategyModel, MetaModel

INDEX_NAME = "esrs-strategies"

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
    Search strategies in Elasticsearch.
    """
    response = utils.search_assets(
        "strategies", project_id, text, filters, sort, size, page
    )
    return response

def tags(project_id: str) -> Dict[str, Any]:
    """
    Search tags for strategies in Elasticsearch.
    """
    es_response = utils.search_tags("strategies", project_id)
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a strategy in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: StrategyModel, _id: str = None) -> Dict[str, Any]:
    """
    Create a strategy in Elasticsearch.
    """

    # Add @meta.created_* fields
    doc = MetaModel.apply_meta_create(doc)
    
    # Create, validate, and dump model
    doc = (
        StrategyModel
        .model_validate(doc)
        .model_dump(by_alias=True, exclude_unset=True)
    )

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("strategies", doc)
    
    # Submit
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: StrategyModel) -> Dict[str, Any]:
    """
    Update a strategy in Elasticsearch.
    """ 
    
    # Add @meta.updated_* fields
    doc_partial = MetaModel.apply_meta_update(doc_partial)
    
    # Create, validate, and dump model
    doc_partial = (
        StrategyModel
        .model_validate(doc_partial, context={"is_partial": True})
        .model_dump(by_alias=True, exclude_unset=True)
    )
    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("strategies", doc_partial)
    
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
    Delete a strategy in Elasticsearch.
    """
    es_response = es("studio").delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True
    )
    return es_response