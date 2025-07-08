# Standard packages
import uuid

# App packages
from server.utils import serialize

def has_valid_meta_for_create(obj, created_by: str = "unknown"):
    return (
        obj.meta is not None and
        obj.meta.created_at is not None and
        obj.meta.created_by == created_by and
        obj.meta.updated_at is None and
        obj.meta.updated_by is None
    )

def has_valid_meta_for_update(obj, created_by: str = "unknown", updated_by: str = "unknown"):
    return (
        obj.meta is not None and
        obj.meta.created_at is not None and
        obj.meta.created_by == created_by and
        obj.meta.updated_at is not None and
        obj.meta.updated_by == updated_by
    )

def is_equal(a, b) -> bool:
    return serialize(a) == serialize(b)
    
def is_uuid(s: str) -> bool:
    try:
        return str(uuid.UUID(s)) == s
    except ValueError:
        return False