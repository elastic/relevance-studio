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

ACCEPTED_TYPES_FOR_INVALID_VALUES = set([
    "bool",
    "string",
    "int",
    "int_ge_0",
    "int_ge_1",
    "float",
    "float_ge_0",
    "float_ge_1",
    "number",
    "number_ge_0",
    "number_ge_1",
    "object",
    "list_of_strings",
    "list_of_objects",
])

def invalid_values_for(
        type: str,
        allow_empty: bool = False,
        allow_null: bool = False,
    ):
    if type not in ACCEPTED_TYPES_FOR_INVALID_VALUES:
        raise Exception(f"{type} is not a valid type")
    
    strings = [ "0", "1", "true", "false", "null", "test" ]
    strings_empty = [ "", " " ]
    ints = [ -1, 0, 1 ]
    floats = [ -3.14, 0.0, 3.14 ]
    numbers = list(ints) + list(floats)
    bools = [ True, False ]
    objects = [ { "a": "b" } ]
    objects_empty = [ {} ]
    list_of_strings = [ list([ s for s in strings ]) + list([ s for s in strings_empty ] if allow_empty else []) ]
    list_of_objects = [ list([ o for o in objects ]) + list([ o for o in objects_empty ] if allow_empty else []) ]
    list_empty = [ [] ]
    
    invalid_values = []
    if not allow_null:
        invalid_values.append(None)
    if type == "string":
        invalid_values += list(numbers)
        invalid_values += list(bools)
        invalid_values += list(objects)
        invalid_values += list(objects_empty)
        invalid_values += list(list_of_strings)
        invalid_values += list(list_of_objects)
        invalid_values += list(list_empty)
        if not allow_empty:
            invalid_values += list(strings_empty)
    elif type.startswith("int"):
        invalid_values += list(bools)
        invalid_values += list(floats)
        invalid_values += list(objects)
        invalid_values += list(objects_empty)
        invalid_values += list(list_of_strings)
        invalid_values += list(list_of_objects)
        invalid_values += list(list_empty)
        invalid_values += list(strings)
        invalid_values += list(strings_empty)
        if type.endswith("_ge_0"):
            invalid_values += list([ n for n in ints if n < 0 ])
        elif type.endswith("_ge_1"):
            invalid_values += list([ n for n in ints if n < 1 ])
    elif type.startswith("float"):
        invalid_values += list(bools)
        invalid_values += list(ints)
        invalid_values += list(objects)
        invalid_values += list(objects_empty)
        invalid_values += list(list_of_strings)
        invalid_values += list(list_of_objects)
        invalid_values += list(list_empty)
        invalid_values += list(strings)
        invalid_values += list(strings_empty)
        if type.endswith("_ge_0"):
            invalid_values += list([ n for n in floats if n < 0 ])
        elif type.endswith("_ge_1"):
            invalid_values += list([ n for n in floats if n < 1 ])
    elif type.startswith("number"):
        invalid_values += list(bools)
        invalid_values += list(objects)
        invalid_values += list(objects_empty)
        invalid_values += list(list_of_strings)
        invalid_values += list(list_of_objects)
        invalid_values += list(list_empty)
        invalid_values += list(strings)
        invalid_values += list(strings_empty)
        if type.endswith("_ge_0"):
            invalid_values += list([ n for n in numbers if n < 0 ])
        elif type.endswith("_ge_1"):
            invalid_values += list([ n for n in numbers if n < 1 ])
    elif type == "object":
        invalid_values += list(bools)
        invalid_values += list(numbers)
        invalid_values += list(list_of_strings)
        invalid_values += list(list_of_objects)
        invalid_values += list(list_empty)
        invalid_values += list(strings)
        invalid_values += list(strings_empty)
        if not allow_empty:
            invalid_values += list(objects_empty)
    elif type == "list_of_strings":
        invalid_values += list(bools)
        invalid_values += list(numbers)
        invalid_values += list(objects)
        invalid_values += list(objects_empty)
        invalid_values += list(strings)
        invalid_values += list(strings_empty)
        invalid_values += list(list_of_objects)
        if not allow_empty:
            invalid_values += list(list_empty)
    elif type == "list_of_objects":
        invalid_values += list(bools)
        invalid_values += list(numbers)
        invalid_values += list(objects)
        invalid_values += list(objects_empty)
        invalid_values += list(strings)
        invalid_values += list(strings_empty)
        invalid_values += list(list_of_strings)
        if not allow_empty:
            invalid_values += list(list_empty)
    return invalid_values