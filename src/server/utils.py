# Standard packages
import json
import re
import time
import uuid
from datetime import datetime, timezone
from hashlib import blake2b

# Pre-compiled regular expressions
RE_PARAMS = re.compile(r"{{\s*([\w.]+)\s*}}")

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

def timestamp(t=None):
    """
    Generate a @timestamp value, optional from a given time object.
    """
    t = t or time.time()
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat().replace("+00:00", "Z")

def extract_params(obj):
    """
    Extract Mustache variable params from an object serialized as json.
    """
    return list(set(re.findall(RE_PARAMS, json.dumps(obj))))