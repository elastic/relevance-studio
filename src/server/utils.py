# Standard packages
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Dict, List

# Third-party packages
from .client import es

# Pre-compiled regular expressions
RE_PARAMS = re.compile(r"{{\s*([\w.]+)\s*}}")

ASSET_TYPES = set([
    "projects",
    "displays",
    "scenarios",
    "judgements",
    "strategies",
    "benchmarks",
    "evaluations",
])
ASSET_TYPES_RELATIONAL_ID_NAMES = {
    "projects": "project_id",
    "displays": "display_id",
    "scenarios": "scenario_id",
    "judgements": "judgement_id",
    "strategies": "strategy_id",
    "benchmarks": "benchmark_id",
    "evaluations": "evaluation_id",
}

def unique_id(input=None):
    """
    Generate a unique ID, either randomly when input=is None or
    deterministically when input is not None.
    """
    if input is None:
        return str(uuid.uuid4())
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint(input)))

def fingerprint(obj):
    """
    Generate a determinsitic fingerprint of an object:
    
    1. Serialize the object as JSON deterministically.
    2. Calculate a 128-bit BLAKE2b digest of the serialized value.
    
    """
    return blake2b((serialize(obj)).encode(), digest_size=16).hexdigest()

def serialize(obj):
    """
    Serialize an object as JSON without whitespace and with sorted keys as a
    standard and deterministic form of serialization.
    """
    return json.dumps(obj, separators=(',', ':'), sort_keys=True)

def timestamp(t: float = None):
    """
    Generate a @timestamp value, optional from a given time object.
    """
    t = t or time.time()
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat().replace("+00:00", "Z")

def extract_params(obj: Dict[str, Any]):
    """
    Extract Mustache variable params from an object serialized as json.
    """
    return sorted(list(set(re.findall(RE_PARAMS, json.dumps(obj)))))

def copy_fields_to_search(doc: Dict[str, Any], fields: List[str]):
    """
    Given a doc and a list of field names, if any of those fields exist in the
    doc, copy the value to a field with the same name under "_search" and
    serialize the value as a string. The purpose is to provide a consistent
    way of storing fields in a format suitable for full text search, regardless
    of whether the original value was a string, object, or list. Those field
    types have inconsistent support for copy_to or multifields in Elasticsearch.
    """
    for field in fields:
        value = doc.get(field)
        if not value and value != 0: # skip {}, [], "", True, False
            continue
        if "_search" not in doc:
            doc["_search"] = {}
        if isinstance(value, (dict, list)):
            doc["_search"][field] = json.dumps(value)
        else:
            doc["_search"][field] = str(value)
    return doc

def get_search_fields_from_mapping(template_name: str) -> List[str]:
    """
    Return all field names defined under the "_search" field of the mapping of
    an index template. This helps automate the use of copy_fields_to_search().
    """
    path_base = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "elastic", "index_templates"
    )
    path_index_template = os.path.join(path_base, f"{template_name}.json")
    with open(path_index_template, 'r') as f:
        data = json.load(f)
    return sorted(list(
        data
        .get("template", {})
        .get("mappings", {})
        .get("properties", {})
        .get("_search", {})
        .get("properties", {})
        .keys()
    ))
    
def remove_empty_values(obj, keep_fields=None, path=""):
    """
    Recursively remove all fields from a nested object whose values are
    None, "", [], or {} — unless they are listed in ignored_fields
    (supports dot notation). Use this before creating or updating docs in
    Elasticsearch.
    """
    if keep_fields is None:
        keep_fields = set()
    else:
        keep_fields = set(keep_fields)
    def current_path(key):
        return key if path == "" else f"{path}.{key}"
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            full_path = current_path(k)
            cleaned_value = remove_empty_values(v, keep_fields, full_path)
            if full_path in keep_fields:
                cleaned[k] = v
            elif cleaned_value not in (None, ""):# (None, "", [], {}):
                cleaned[k] = cleaned_value
        return cleaned
    elif isinstance(obj, list):
        return [
            remove_empty_values(item, keep_fields, path)
            for item in obj
        ]
    else:
        return obj
    
def search_tags(asset_type: str, project_id: str = None) -> Dict[str, Any]:
    """
    Standardizes retrieval for tags() API of project assets.
    """
    if asset_type not in ASSET_TYPES:
        raise Exception(f"\"{asset_type}\" is not a valid project asset type.")
    
    # Prepare search
    body = {}
    
    # Only return aggs
    body["size"] = 0
    
    # Filter query by project_id
    if asset_type == "projects":
        body["query"] = { "bool": { "filter": [{ "ids": { "values": [ project_id ]}}]}}
    else:
        if not project_id:
            raise Exception(f"\"project_id\" is required to scope searches.")
        body["query"] = { "bool": { "filter": [{ "term": { "project_id": project_id }}]}}
        
    # Return all tags (up to a max of 10,000)
    body["aggs"] = {
        "tags": {
            "terms": {
                "field": "tags",
                "size": 10000,
                "order": { "_key": "asc" }
            }
        }
    }
        
    # Submit search
    es_response = es("studio").search(
        index=f"esrs-{asset_type}",
        body=body
    )
    return es_response
    
def search_assets(
        asset_type: str,
        project_id: str = None,
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        counts: List[str] = [],
    ) -> Dict[str, Any]:
    """
    Standardizes basic searches and aggs for the search() API of project assets.
    
    Structure of the sort input (single field allowed):
    
    {
        SORT_FIELD: SORT_ORDER
    }
    
    
    Structure of the counts input, which defines which assets to count that
    share a relation by _id to the given asset:
    
    [
        RELATIONAL_ASSET_TYPE,
        ...
    ]
    """
    if asset_type not in ASSET_TYPES:
        raise Exception(f"\"{asset_type}\" is not a valid project asset type.")
    if counts:
        for relational_asset_type in counts:
            if relational_asset_type not in ASSET_TYPES:
                raise Exception(f"\"{relational_asset_type}\" is not a valid project asset type.")
    
    # Prepare search
    body = {}
    
    # Filter search by project_id
    if asset_type != "projects":
        if not project_id:
            raise Exception(f"\"project_id\" is required to scope searches.")
        body["query"] = { "bool": { "filter": [{ "term": { "project_id": project_id }}]}}
        
    # Apply any given filers
    for filter in filters or []:
        body.setdefault("query", {}).setdefault("bool", {}).setdefault("filter", [])
        body["query"]["bool"]["filter"].append(filter)
    
    # Exclude fields that exist only for searchability
    body["_source"] = { "excludes": [ "_search" ]}
    
    # Apply pagination
    body["size"] = size
    body["from"] = (page - 1) * size
    
    # Apply text if given
    if text:
        body.setdefault("query", {}).setdefault("bool", {}).setdefault("must", [])
        body["query"]["bool"]["must"].append({
            "query_string": {
                "query": text,
                "default_operator": "AND",
                "fields": [ "*", "_search.*" ]
            }
        })
    
    # Apply sort if given
    if sort:
        body["sort"] = [{ sort["field"]: sort["order"] }]
        
    # Submit search
    es_response = es("studio").search(
        index=f"esrs-{asset_type}",
        body=body
    )
    if not counts:
        return es_response
    
    # Prepare aggs
    body = {}
    body["size"] = 0
    
    # Filter by _ids of hits
    _id_name = ASSET_TYPES_RELATIONAL_ID_NAMES[asset_type]
    _ids = [ hit["_id"] for hit in es_response.body["hits"]["hits"] ]
    body["query"] = { "terms": { _id_name: _ids }}
    body["aggs"] = { "counts": {}}
    
    # Aggregate by those _ids
    body["aggs"]["counts"]["terms"] = { "field": _id_name, "size": size }
    body["aggs"]["counts"]["aggs"] = {}
    
    # Count assets that reference those _ids as a relation
    indices = []
    for relational_asset_type in counts:
        body["aggs"]["counts"]["aggs"][relational_asset_type] = {
            "filter": { "term": {  "_index": f"esrs-{relational_asset_type}" }}
        }
        indices.append(f"esrs-{relational_asset_type}")
    aggs_response = es("studio").search(
        index=",".join(indices),
        body=body
    )
    
    # Merge aggs with _search response if there were any aggregations found
    if "aggregations" in aggs_response.body:
        es_response.body["aggregations"] = aggs_response.body["aggregations"]
    return es_response