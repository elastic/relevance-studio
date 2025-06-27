# Standard packages
from typing import Any, Dict, List

# App packages
from .. import utils
from ..client import es
from ..models import StrategyModel

INDEX_NAME = "esrs-strategies"
SEARCH_FIELDS = utils.get_search_fields_from_mapping("strategies")

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
    # Always use the latest timestamp
    doc = doc.model_copy(update={"timestamp_": utils.timestamp()})
    # Copy searchable fields to _search
    doc_dict = doc.model_dump(by_alias=True, exclude_unset=True)
    doc_dict = utils.copy_fields_to_search(doc_dict, SEARCH_FIELDS)
    doc_dict = utils.remove_empty_values(doc_dict)
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id or utils.unique_id(),
        document=doc_dict,
        refresh=True
    )
    return es_response

def update(_id: str, doc: StrategyModel) -> Dict[str, Any]:
    """
    Update a strategy in Elasticsearch.
    """ 
    # Always use the latest timestamp
    doc = doc.model_copy(update={"timestamp_": utils.timestamp()})
    # Copy searchable fields to _search
    doc_dict = doc.model_dump(by_alias=True, exclude_unset=True)
    doc_dict = utils.copy_fields_to_search(doc_dict, SEARCH_FIELDS)
    doc_dict = utils.remove_empty_values(doc_dict)
    # For some reason, index() is needed instead of update(), otherwise the
    # updated template doesn't persist in Elasticsearch. This isn't true for
    # displays, though. Perhaps a bug in how documents are updated on fields
    # where type=object and enabled=false. The only difference is that strategy
    # template.source is an object, and display template.body is a string.
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=_id,
        document=doc_dict,
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