# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import DisplayModel

INDEX_NAME = "esrs-displays"
SEARCH_FIELDS = utils.get_search_fields_from_mapping("displays")

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

def create(doc: DisplayModel, _id: str = None) -> Dict[str, Any]:
    """
    Create a display in Elasticsearch. Allow a predetermined _id.
    """
    # Copy searchable fields to _search
    doc_dict = doc.model_dump(by_alias=True, exclude_unset=True)
    doc_dict = utils.copy_fields_to_search(doc_dict, SEARCH_FIELDS)
    doc_dict = utils.remove_empty_values(doc_dict)
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc_dict,
        refresh=True,
    )
    return es_response

def update(_id: str, doc: DisplayModel) -> Dict[str, Any]:
    """
    Update a display in Elasticsearch.
    """
    # Copy searchable fields to _search
    doc_dict = doc.model_dump(by_alias=True, exclude_unset=True)
    doc_dict = utils.copy_fields_to_search(doc_dict, SEARCH_FIELDS)
    doc_dict = utils.remove_empty_values(doc_dict)
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_dict,
        refresh=True,
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