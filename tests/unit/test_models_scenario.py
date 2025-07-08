# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.scenarios import ScenarioModel
from tests.utils import has_valid_meta_for_create, is_equal

def valid_output():
    data = {
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
    data = valid_output()
    data.pop("params")
    return data

class TestScenarioModel:
    def test_valid_output(self):
        try:
            obj = ScenarioModel(**valid_output())
            assert has_valid_meta_for_create(obj)
            actual = obj.model_dump(by_alias=True, mode="json")
            actual.pop("@meta", None)
            assert is_equal(actual, valid_output())
        except Exception as e:
            pytest.fail(f"Unexpected error during instantiation: {e}")
            
    ####  project_id  ##########################################################
            
    def test_output_project_id_invalid_missing(self):
        data = valid_output()
        data.pop("project_id")
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_project_id_invalid_types(self, value):
        data = valid_output()
        data["project_id"] = value
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    ####  name  ################################################################
            
    def test_output_name_invalid_missing(self):
        data = valid_output()
        data.pop("name")
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_name_invalid_types(self, value):
        data = valid_output()
        data["name"] = value
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    ####  params  ##############################################################
            
    def test_input_params_inferred_from_values(self):
        data = valid_input()
        obj = ScenarioModel(**data)
        assert sorted(obj.params) == sorted(list(valid_output()["values"].keys()))

    def test_output_params_must_match_values(self):
        data = valid_output()
        data["params"] = ["text", "wrong"]
        with pytest.raises(ValueError):
            ScenarioModel(**data)
            
    ####  tags  ################################################################
            
    def test_output_tags_valid_missing(self):
        data = valid_output()
        data.pop("tags")
        ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [None, []])
    def test_output_tags_valid_types(self, value):
        data = valid_output()
        data["tags"] = value
        ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [0, "body", True, False, [1], [{}], {} ])
    def test_output_tags_invalid_types(self, value):
        data = valid_output()
        data["tags"] = value
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    ####  values  ##############################################################
            
    def test_output_values_invalid_missing(self):
        data = valid_output()
        data.pop("values")
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    def test_output_values_invalid_empty(self):
        data = valid_output()
        data["values"] = {}
        with pytest.raises(ValidationError):
            ScenarioModel(**data)
            
    @pytest.mark.parametrize("value", [0, "one", None, True, False, [], [{}] ])
    def test_output_values_invalid_types(self, value):
        data = valid_output()
        data["values"] = value
        with pytest.raises(ValidationError):
            ScenarioModel(**data)