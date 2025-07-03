# Standard packages
import uuid

# App packages
from server.utils import serialize

def is_equal(a, b) -> bool:
    return serialize(a) == serialize(b)
    
def is_uuid(s: str) -> bool:
    try:
        return str(uuid.UUID(s)) == s
    except ValueError:
        return False