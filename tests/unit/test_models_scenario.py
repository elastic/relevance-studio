# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.scenarios import ScenarioModel
from tests.utils import is_equal

def valid_doc():
    data = {
        "@timestamp": "2025-07-02T16:41:52.219598Z",
        "project_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "name": "brown oxfords",
        "params": [
            "text"
        ],
        "tags": [
            "body"
        ],
        "values": {
            "text": "brown oxfords"
        }
    }
    return data

def valid_input():
    data = valid_doc()
    data.pop("params")
    return data

class TestScenarioModel:
    def test_valid_instance(self):
        try:
            obj = ScenarioModel(**valid_doc())
            assert is_equal(obj.model_dump(by_alias=True), valid_doc())
        except Exception as e:
            pytest.fail(f"Unexpected error during instantiation: {e}")
            
    ####  project_id  ##########################################################
            
    def test_doc_project_id_invalid_missing(self):
        data = valid_doc()
        data.pop("project_id")
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_project_id_invalid_types(self, value):
        data = valid_doc()
        data["project_id"] = value
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    ####  name  ################################################################
            
    def test_doc_name_invalid_missing(self):
        data = valid_doc()
        data.pop("name")
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_name_invalid_types(self, value):
        data = valid_doc()
        data["name"] = value
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    ####  params  ##############################################################
            
    def test_input_params_inferred_from_values(self):
        data = valid_input()
        obj = ScenarioModel(**data)
        assert sorted(obj.params) == sorted(list(valid_doc()["values"].keys()))

    def test_doc_params_must_match_values(self):
        data = valid_doc()
        data["params"] = ["text", "wrong"]
        with pytest.raises(ValueError):
            ScenarioModel(**data)

    def test_doc_params_none_values_none_valid(self):
        data = valid_doc()
        data["values"] = None
        data["params"] = None
        ScenarioModel(**data)

    def test_doc_params_nonempty_values_none_invalid(self):
        data = valid_doc()
        data["values"] = None
        data["params"] = ["name"]
        with pytest.raises(ValueError):
            ScenarioModel(**data)
            
    ####  tags  ################################################################
            
    def test_doc_tags_valid_missing(self):
        data = valid_doc()
        data.pop("tags")
        ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [None, []])
    def test_doc_tags_valid_types(self, value):
        data = valid_doc()
        data["tags"] = value
        ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [0, "body", True, False, [1], [{}], {} ])
    def test_doc_tags_invalid_types(self, value):
        data = valid_doc()
        data["tags"] = value
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    ####  values  ##############################################################
            
    def test_doc_values_invalid_missing(self):
        data = valid_doc()
        data.pop("values")
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    def test_doc_values_invalid_empty(self):
        data = valid_doc()
        data["values"] = {}
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [0, "one", None, True, False, [], [{}] ])
    def test_doc_values_invalid_types(self, value):
        data = valid_doc()
        data["values"] = value
        with pytest.raises(ValidationError):
            ScenarioModel(**data)