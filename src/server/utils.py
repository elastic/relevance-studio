# Standard packages
import json
import re
import time
import uuid
from datetime import datetime, timezone
from hashlib import blake2b

# Pre-compiled regular expressions
RE_PARAMS = re.compile(r"{{\s*([\w.]+)\s*}}")

def fingerprint(obj):
    """
    Generate a determinsitic fingerprint of an object:
    
    1. Serialize the object as JSON without whitespace and with sorted keys.
    2. Calculate a 128-bit BLAKE2b digest of the serialized value.
    
    """
    serialized = json.dumps(obj, separators=(',', ':'), sort_keys=True)
    digest = blake2b(serialized.encode(), digest_size=16).hexdigest()
    return digest

def unique_id(input=None):
    """
    Generate a unique ID, either randomly when input=is None or
    deterministically when input is not None.
    """
    if input is None:
        return uuid.uuid4()
    return uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint(input))

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