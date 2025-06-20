# Standard packages
from typing import Any, Dict, List

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

def create(
        project_id: str,
        name: str,
        tags: List[str] = [],
        template: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
    """
    Create a strategy in Elasticsearch.
    """
    doc = {
        "@timestamp": utils.timestamp(),
        "project_id": project_id,
        "name": name,
        "tags": tags or [],
        "params": [],
        "template": template,
    }
    if template and "source" in template:
        doc["params"] = utils.extract_params(template["source"])
    es_response = es("studio").index(
        index=INDEX_NAME,
        id=utils.unique_id(),
        document=doc,
        refresh=True
    )
    return es_response

def update(
        _id: str,
        name: str = None,
        tags: List[str] = [],
        template: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
    """
    Update a strategy in Elasticsearch.
    """ 
    doc_updates = {
        "@timestamp": utils.timestamp()
    }
    if name:
        doc_updates["name"] = name
    if tags:
        doc_updates["tags"] = tags
    if template:
        doc_updates["template"] = template
        if "source" in template:
            doc_updates["params"] = utils.extract_params(template["source"])
        else:
            doc_updates["params"] = []
    es_response = es("studio").update(
        index=INDEX_NAME,
        id=_id,
        doc=doc_updates,
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