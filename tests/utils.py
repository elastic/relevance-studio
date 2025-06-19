import uuid

def is_uuid(s):
    try:
        return str(uuid.UUID(s)) == s
    except ValueError:
        return False