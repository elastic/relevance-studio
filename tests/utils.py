# Standard packages
import uuid

def assert_valid_meta_for_create(meta, created_by: str = "unknown"):
    assert meta is not None
    assert meta.get("created_at") is not None
    assert meta.get("created_by") == created_by
    assert "updated_at" in meta
    assert meta["updated_at"] is None
    assert "updated_by" in meta
    assert meta["updated_by"] is None

def assert_valid_meta_for_update(meta, updated_by: str = "unknown"):
    assert meta is not None
    assert "created_at" not in meta
    assert "created_by" not in meta
    assert meta.get("updated_at") is not None
    assert meta.get("updated_by") == updated_by
    
def is_uuid(s: str) -> bool:
    try:
        return str(uuid.UUID(s)) == s
    except ValueError:
        return False
    
def mock_context():
    """
    Returns a mock context.
    """
    context = { "user": "test-user" }
    return context