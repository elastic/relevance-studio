# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict

# App packages
from .. import utils
from ..client import es

def _flatten_fields(properties, parent_key=""):
    """Recursively flattens the field mapping, ignoring multi-fields.

    Multi-fields are ignored as they aren't visible in _source and are not needed
    for configuring document displays in the UX.

    Args:
        properties: The properties dictionary from the Elasticsearch mapping.
        parent_key: The parent key for nested fields.

    Returns:
        A flattened dictionary mapping field names to their types.
    """
    fields = {}
    for key, value in properties.items():
        full_key = f"{parent_key}.{key}" if parent_key else key
        if "properties" in value:
            fields.update(_flatten_fields(value["properties"], full_key))
        elif "type" in value:
            fields[full_key] = value["type"]
        # Commented out because we want to ignore multi-fields in the UX
        #elif "fields" in value:
        #    if "type" in value:
        #        fields[full_key] = value["type"]
        #    for subfield, subvalue in value["fields"].items():
        #        sub_key = f"{full_key}.{subfield}"
        #        fields[sub_key] = subvalue.get("type", "object")
        else:
            fields[full_key] = "object"
    return fields

def search(index_patterns: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Submit a search request to the content deployment.

    Args:
        index_patterns: Comma-separated string of index patterns.
        body: The Elasticsearch search request body.

    Returns:
        The search response from Elasticsearch.
    """
    es_response = es("content").search(
        index=index_patterns,
        body=body
    )
    return es_response

def get(index_patterns: str) -> Dict[str, Any]:
    """Retrieve indices with their settings and mappings from the content deployment.

    Args:
        index_patterns: Comma-separated string of index patterns.

    Returns:
        A dictionary of indices with their settings and mappings.
    """
    response = es("content").options(ignore_status=404).indices.get(index=index_patterns)
    if response.get("status") == 404:
        return {}
    return response.body

def mappings_browse(index_patterns: str) -> Dict[str, Any]:
    """Retrieve flattened index mappings for browsing.

    Args:
        index_patterns: Comma-separated string of index patterns.

    Returns:
        A dictionary mapping index names to their flattened fields and types.
    """
    response = es("content").options(ignore_status=404).indices.get_mapping(index=index_patterns)
    if response.get("status") == 404:
        return {}
    mappings = response.body
    indices = {}
    for index, mapping in mappings.items():
        fields = mapping["mappings"].get("properties", {})
        fields_flattened = _flatten_fields(fields)
        indices[index] = { "fields": fields_flattened }
    return indices

def make_index_relevance_fingerprints(index_pattern: str) -> Dict[str, Any]:
    """Generate relevance fingerprints for indices in an index pattern.

    Args:
        index_pattern: The Elasticsearch index pattern to analyze.

    Returns:
        A dictionary mapping index names to their relevance fingerprints and shard info.
    """
    
    # Create a fingerprint for each index in the given index pattern
    indices = get(index_pattern)
    stats = es("content").indices.stats(index=index_pattern, level="shards")
    result = {}
    for index_name in indices.keys():
        if index_name not in stats["indices"]:
            continue
        index_uuid = indices[index_name]["settings"]["index"]["uuid"]

        # Collect and deduplicate max_seq_no by shard
        shard_seq_nos = []
        shards = stats["indices"][index_name]["shards"]
        for shard_id, shard_copies in shards.items():
            for copy in shard_copies:
                max_seq_no = copy.get("seq_no", {}).get("max_seq_no")
                shard_seq_nos.append((int(shard_id), max_seq_no))

        shard_maxes = {}
        for shard_id, seq_no in shard_seq_nos:
            shard_maxes[shard_id] = max(seq_no, shard_maxes.get(shard_id, -1))

        # Prepare the data for hashing, ensuring that shards are sorted by id
        # for deterministic hashing.
        shard_list = [
            {"id": shard_id, "max_seq_no": seq_no}
            for shard_id, seq_no in sorted(shard_maxes.items())
        ]
        result[index_name] = {
            "_index": index_name,
            "_fingerprint": utils.fingerprint({
                "index": index_name,
                "uuid": index_uuid,
                "shards": shard_list
            }),
            "aliases": indices[index_name].get("aliases") or {},
            "settings": indices[index_name].get("settings") or {},
            "mappings": indices[index_name].get("mappings") or {},
            "shards": shard_list
        }
    return result