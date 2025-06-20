# Standard packages
from typing import Any, Dict

# App packages
from .. import utils
from ..client import es

def _flatten_fields(properties, parent_key=""):
    """
    Recursively flattens the field mapping, ignoring multi-fields which
    aren"t visible in _source and therefore not needed for configuring
    the display of documents.
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
    """
    Submit a search request to the content deployment.
    """
    es_response = es("content").search(
        index=index_patterns,
        body=body
    )
    return es_response

def mappings_browse(index_patterns: str) -> Dict[str, Any]:
    """
    Given a comma-separated string of index patterns for the content deployment,
    return the matching indices with their fields and types in a flat structure.
    """
    
    # Get matching indices and their mappings
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
    """
    Generate a relevance fingerprint for all indices in a given index pattern.
    
    Structure of the output object:
    
    {
        INDEX_NAME: {
            "fingerprint": STRING,
            "shards": [
                {
                    "id": SHARD_ID,
                    "max_seq_no": MAX_SEQ_NO
                },
                ...
            ],
            "uuid": INDEX_UUID
        },
        ...
    }
    
    Example output for an index pattern "products-*":
     
    {
        "products-2025": {
            "fingerprint": "c1d9b14ae26538325d2bb56471497844",
            "shards": [
                { "id": 0, "max_seq_no": 111 },
                { "id": 1, "max_seq_no": 112 }
            ],
            "uuid": "abc123..."
        },
        "products-2024": {
            "fingerprint": "03f758f51a1bae0ce87125ea295785a4",
            "shards": [
                { "id": 0, "max_seq_no": 301 }
            ],
            "uuid": "def456..."
        }
    }
    """
    
    # Create a fingerprint for each index in the given index pattern
    settings = es("content").indices.get_settings(index=index_pattern)
    stats = es("content").indices.stats(index=index_pattern, level="shards")
    fingerprints = {}
    for index_name in settings.keys():
        if index_name not in stats["indices"]:
            continue
        index_uuid = settings[index_name]["settings"]["index"]["uuid"]

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

        # Prepare the data for hashing
        shard_list = [
            {"id": shard_id, "max_seq_no": seq_no}
            for shard_id, seq_no in sorted(shard_maxes.items())
        ]
        fingerprint_obj = {
            "index": index_name,
            "uuid": index_uuid,
            "shards": shard_list
        }

        # Include the digest in the result
        fingerprints[index_name] = {
            **fingerprint_obj,
            "fingerprint": utils.fingerprint(fingerprint_obj)
        }
    return fingerprints