# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import DisplayCreate, DisplayUpdate

INDEX_NAME = "esrs-displays"

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
        "displays", project_id, text, filters, sort, size, page
    )
    return response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a display in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id,
        source_excludes="_search",
    )
    return es_response

def create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    """
    Create a display in Elasticsearch. Allow a predetermined _id.
    """
    
    # Create, validate, and dump model
    doc = DisplayCreate.model_validate(doc).serialize()

    # Copy searchable fields to _search
    doc = utils.copy_fields_to_search("displays", doc)
    
    # Submit
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc,
        refresh=True,
    )
    return es_response

def update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a display in Elasticsearch.
    """
    
    # Create, validate, and dump model
    doc_partial = DisplayUpdate.model_validate(doc_partial).serialize()

    
    # Copy searchable fields to _search
    doc_partial = utils.copy_fields_to_search("displays", doc_partial)
    
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
    Delete a display in Elasticsearch.
    """
    es_response = es("studio").delete(
        index=INDEX_NAME,
        id=_id,
        refresh=True,
    )
    return es_response