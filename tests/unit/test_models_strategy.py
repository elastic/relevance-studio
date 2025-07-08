# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.strategies import StrategyModel
from tests.utils import has_valid_meta_for_create, is_equal

def valid_output():
    data = {
        "project_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "name": "Classical - Name match",
        "params": [
            "text"
        ],
        "tags": [
            "bm25"
        ],
        "template": {
            "source": """{"retriever":{"standard":{"query":{"match":{"name.text":{"query":"{{ text }}"}}}}}}"""
        }
    }
    return data

def valid_input():
    data = valid_output()
    data.pop("params")
    return data

class TestStrategyModel:
    def test_valid_output(self):
        try:
            obj = StrategyModel(**valid_output())
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
            StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_project_id_invalid_types(self, value):
        data = valid_output()
        data["project_id"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    ####  name  ################################################################
            
    def test_output_name_invalid_missing(self):
        data = valid_output()
        data.pop("name")
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_name_invalid_types(self, value):
        data = valid_output()
        data["name"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    ####  params  ##############################################################
    
    def test_output_params_must_match_values(self):
        data = valid_output()
        data["params"] = ["text", "wrong"]
        with pytest.raises(ValueError):
            StrategyModel(**data)
            
    ####  tags  ################################################################
            
    def test_output_tags_valid_missing(self):
        data = valid_output()
        data.pop("tags")
        StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [None, []])
    def test_output_tags_valid_types(self, value):
        data = valid_output()
        data["tags"] = value
        StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, "body", True, False, [1], [{}], {} ])
    def test_output_tags_invalid_types(self, value):
        data = valid_output()
        data["tags"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    ####  template  ############################################################
            
    def test_output_template_invalid_missing(self):
        data = valid_output()
        data.pop("template")
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, "body", True, False, [1], [{}]])
    def test_output_template_invalid_types(self, value):
        data = valid_output()
        data["template"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)