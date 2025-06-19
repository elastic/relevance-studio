# Standard packages
from typing import Any, Dict

# App packages
from .. import utils
from ..client import es

INDEX_NAME = "esrs-strategies"

def browse(project_id: str, size: int = 10000) -> Dict[str, Any]:
    """
    List strategies in Elasticsearch.
    """
    body={
        "query": {
            "bool": {
                "filter": {
                    "term": {
                        "project_id": project_id
                    }
                }
            }
        },
        "size": size
    }
    es_response = es("studio").search(
        index=INDEX_NAME,
        body=body,
        ignore_unavailable=True
    )
    return es_response

def get(_id: str) -> Dict[str, Any]:
    """
    Get a strategy in Elasticsearch.
    """
    es_response = es("studio").get(
        index=INDEX_NAME,
        id=_id
    )
    return es_response

def create(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a strategy in Elasticsearch.
    """
    doc.pop("_id", None) # es doesn't want _id in doc
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id(),
        document=doc,
        refresh=True
    )
    return es_response

def update(_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a strategy in Elasticsearch.
    """
    doc.pop("_id", None) # es doesn't want _id in doc
    doc["params"] = utils.extract_params(doc["template"]["source"])
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc,
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