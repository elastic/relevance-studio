# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

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
RE_PARAMS = re.compile(r"{{\s*([\w.-]+)\s*}}")

ASSET_TYPES = set([
    "conversations",
    "workspaces",
    "displays",
    "scenarios",
    "judgements",
    "strategies",
    "benchmarks",
    "evaluations",
])
ASSET_TYPES_RELATIONAL_ID_NAMES = {
    "conversations": "conversation_id",
    "workspaces": "workspace_id",
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

def copy_fields_to_search(template_name: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Copy values from the doc into the _search field, based on the _search fields defined
    in the specified index template. Automatically infers which fields need stringification.
    """
    field_types = get_search_field_types_from_mapping(template_name)

    def is_empty(val: Any) -> bool:
        return val is None or val == "" or val == {} or val == []

    def serialize_leaf(val: Any) -> str:
        if is_empty(val):
            return ""
        if isinstance(val, str):
            return val
        return json.dumps(val)

    def serialize_array(vals: List[Any]) -> List[str]:
        return [serialize_leaf(v) for v in vals]

    def set_nested_value(obj: Dict[str, Any], path: List[str], value: Any):
        for key in path[:-1]:
            obj = obj.setdefault(key, {})
        obj[path[-1]] = value

    def copy_recursively(value: Any, types: Any, path: List[str]):
        if isinstance(types, str):  # leaf field like "text"
            if isinstance(value, list):
                set_nested_value(doc["_search"], path, serialize_array(value))
            else:
                set_nested_value(doc["_search"], path, serialize_leaf(value))
        elif isinstance(types, dict) and isinstance(value, dict):
            for k, v in value.items():
                if k in types:
                    copy_recursively(v, types[k], path + [k])

    doc.setdefault("_search", {})
    for field, type_info in field_types.items():
        if field in doc:
            copy_recursively(doc[field], type_info, [field])
    return doc

def get_search_fields_from_mapping(template_name: str) -> List[str]:
    """
    Return a list of top-level field names defined under the "_search" section
    of an index template. These are the names passed to copy_fields_to_search().
    """
    path_base = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "elastic", "index_templates"
    )
    path_index_template = os.path.join(path_base, f"{template_name}.json")
    with open(path_index_template, 'r') as f:
        data = json.load(f)
    props = (
        data
        .get("template", {})
        .get("mappings", {})
        .get("properties", {})
        .get("_search", {})
        .get("properties", {})
    )
    return sorted(props.keys())

def get_search_field_types_from_mapping(template_name: str) -> Dict[str, Any]:
    """
    Return a nested dict of _search field types based on the mapping, preserving structure.
    For example:
      { "template": { "source": "text" }, "tags": "text" }
    """
    path_base = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "elastic", "index_templates"
    )
    path_index_template = os.path.join(path_base, f"{template_name}.json")
    with open(path_index_template, 'r') as f:
        data = json.load(f)
    props = (
        data
        .get("template", {})
        .get("mappings", {})
        .get("properties", {})
        .get("_search", {})
        .get("properties", {})
    )
    def walk(p):
        result = {}
        for k, v in p.items():
            if "type" in v and v["type"] != "object":
                result[k] = v["type"]
            elif "properties" in v:
                result[k] = walk(v["properties"])
            else:
                result[k] = "object"
        return result
    return walk(props)
    
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
    
def search_tags(asset_type: str, workspace_id: str = None) -> Dict[str, Any]:
    """
    Standardizes retrieval for tags() API of workspace assets.
    """
    if asset_type not in ASSET_TYPES:
        raise Exception(f"\"{asset_type}\" is not a valid workspace asset type.")
    
    # Prepare search
    body = {}
    
    # Only return aggs
    body["size"] = 0
    
    # Filter query by workspace_id
    if asset_type == "workspaces":
        body["query"] = { "bool": { "filter": [{ "ids": { "values": [ workspace_id ]}}]}}
    else:
        if not workspace_id:
            raise Exception(f"\"workspace_id\" is required to scope searches.")
        body["query"] = { "bool": { "filter": [{ "term": { "workspace_id": workspace_id }}]}}
        
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
        workspace_id: str = None,
        text: str = "",
        filters: List[Dict[str, Any]] = [],
        sort: Dict[str, Any] = {},
        size: int = 10,
        page: int = 1,
        counts: List[str] = [],
    ) -> Dict[str, Any]:
    """
    Standardizes basic searches and aggs for the search() API of workspace assets.
    
    Structure of the sort input (single field allowed):
    
    {
        "field": SORT_FIELD,
        "order": SORT_ORDER
    }
    
    
    Structure of the counts input, which defines which assets to count that
    share a relation by _id to the given asset:
    
    [
        RELATIONAL_ASSET_TYPE,
        ...
    ]
    """
    if asset_type not in ASSET_TYPES:
        raise Exception(f"\"{asset_type}\" is not a valid workspace asset type.")
    if counts:
        for relational_asset_type in counts:
            if relational_asset_type not in ASSET_TYPES:
                raise Exception(f"\"{relational_asset_type}\" is not a valid workspace asset type.")
    
    # Prepare search
    body = {}
    
    # Filter search by workspace_id
    if asset_type not in ["workspaces", "conversations"]:
        if not workspace_id:
            raise Exception(f"\"workspace_id\" is required to scope searches on workspace assets.")
        body["query"] = { "bool": { "filter": [{ "term": { "workspace_id": workspace_id }}]}}
        
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
        if "field" in sort and "order" in sort:
            body["sort"] = [{ sort["field"]: sort["order"] }]
        else:
            body["sort"] = [sort]
        
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

def attach_schema_doc(cls):
    """
    Decorator that attaches the JSON schema of a Pydantic model
    to its own docstring.
    """
    base_doc = cls.__doc__ or ""
    schema = cls.model_json_schema()
    cls.__doc__ = base_doc.rstrip() + "\n\nJSON Schema:\n" + str(schema)
    return cls