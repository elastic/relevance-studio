"""
- utils.remove_empty_values
- utils.get_search_fields_from_mapping
- utils.copy_fields_to_search
- utils.extract_params
- utils.timestamp
- utils.timestamp_given
"""

# Standard packages
import re
import uuid

# App packages
from .test_models_project import valid_output
from server import utils

RE_ISO_8601_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

def sample_obj():
    obj = {
        "null": None,
        "bool": {
            "true": True,
            "false": False
        },
        "number": {
            "int_positive": 1,
            "int_negative": -1,
            "float_positive": 3.14,
            "float_negative": -3.14,
            "zero": 0
        },
        "string": {
            "empty": "",
            "given": "foo"
        },
        "array": {
            "empty": [],
            "empty_string": [""],
            "given": [ "foo", "bar", "baz" ]
        },
        "object": {
            "empty": {},
            "given": {
                "foo": "a",
                "bar": "b",
                "baz": {
                    "x": "y"
                }
            }
        },
        "object_array": {
            "empty": [{}],
            "given": [
                {
                    "foo": "a",
                    "bar": "b",
                    "baz": {
                        "x": "y",
                        "a": "b"
                    }
                },
                {
                    "foo": "{{ param_foo }}",
                    "bar": "{{ param_bar }}"
                }
            ]
        }
    }
    return obj

class TestUtils:
    
    def test_serialize(self):
        given = sample_obj()
        actual = utils.serialize(given)
        expected = """{"array":{"empty":[],"empty_string":[""],"given":["foo","bar","baz"]},"bool":{"false":false,"true":true},"null":null,"number":{"float_negative":-3.14,"float_positive":3.14,"int_negative":-1,"int_positive":1,"zero":0},"object":{"empty":{},"given":{"bar":"b","baz":{"x":"y"},"foo":"a"}},"object_array":{"empty":[{}],"given":[{"bar":"b","baz":{"a":"b","x":"y"},"foo":"a"},{"bar":"{{ param_bar }}","foo":"{{ param_foo }}"}]},"string":{"empty":"","given":"foo"}}"""
        assert actual == expected
    
    def test_fingerprint(self):
        given = sample_obj()
        actual = utils.fingerprint(given)
        expected = "1d3bd7e15ff879a12966740e5db08ff5"
        assert actual == expected
    
    def test_unique_id(self):
        actual = utils.unique_id()
        assert uuid.UUID(actual) # should not raise error
    
    def test_unique_id_given(self):
        given = sample_obj()
        actual = utils.unique_id(given)
        expected = "ef19e3a4-5e4c-5cac-a373-a4272b439089"
        assert actual == expected
    
    def test_timestamp(self):
        actual = utils.timestamp()
        assert RE_ISO_8601_TIMESTAMP.match(actual)
    
    def test_timestamp_given(self):
        given = 1751553902.19001
        actual = utils.timestamp(given)
        expected = "2025-07-03T14:45:02.190010Z"
        assert actual == expected
    
    def test_extract_params(self):
        given = sample_obj()
        actual = utils.extract_params(given)
        expected = [ "param_bar", "param_foo" ]
        assert actual == expected
    
    def test_extract_params_none(self):
        given = sample_obj()
        actual = utils.extract_params(given["object"])
        expected = []
        assert actual == expected
    
    def test_remove_empty_values(self):
        given = sample_obj()
        actual = utils.remove_empty_values(given)
        expected = {"array":{"empty":[],"empty_string":[""],"given":["foo","bar","baz"]},"bool":{"false":False,"true":True},"number":{"float_negative":-3.14,"float_positive":3.14,"int_negative":-1,"int_positive":1,"zero":0},"object":{"empty":{},"given":{"bar":"b","baz":{"x":"y"},"foo":"a"}},"object_array":{"empty":[{}],"given":[{"bar":"b","baz":{"a":"b","x":"y"},"foo":"a"},{"bar":"{{ param_bar }}","foo":"{{ param_foo }}"}]},"string":{"given":"foo"}}
        assert actual == expected
    
    def test_remove_empty_values_keep_fields(self):
        given = sample_obj()
        actual = utils.remove_empty_values(given, keep_fields=[ "null", "array.empty" ])
        expected = {"array":{"empty":[],"empty_string":[""],"given":["foo","bar","baz"]},"bool":{"false":False,"true":True},"null":None,"number":{"float_negative":-3.14,"float_positive":3.14,"int_negative":-1,"int_positive":1,"zero":0},"object":{"empty":{},"given":{"bar":"b","baz":{"x":"y"},"foo":"a"}},"object_array":{"empty":[{}],"given":[{"bar":"b","baz":{"a":"b","x":"y"},"foo":"a"},{"bar":"{{ param_bar }}","foo":"{{ param_foo }}"}]},"string":{"given":"foo"}}
        assert actual == expected
    
    def test_get_search_fields_from_mapping(self):
        actual = utils.get_search_fields_from_mapping("projects")
        expected = sorted([ "name", "index_pattern", "params" ])
        assert actual == expected
    
    def test_copy_fields_to_search(self):
        given = valid_output()
        actual = utils.copy_fields_to_search("projects", given)
        expected = valid_output()
        expected["_search"] = {
            "name": expected["name"],
            "index_pattern": expected["index_pattern"],
            "params": expected["params"],
        }
        assert actual == expected