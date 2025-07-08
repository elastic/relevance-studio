# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.displays import DisplayModel
from tests.utils import has_valid_meta_for_create, is_equal

def valid_output():
    data = {
        "project_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "index_pattern": "products",
        "fields": [
            "category.keyword",
            "description.text",
            "name.text",
         ],
        "template": {
            "body": """### {{name.text}}
*{{category.keyword}}*
{{description.text}}""",
            "image": {
              "position": "top-right",
              "url": "http://localhost:8080/{{_id}}.png"
            }
          }
        }
    return data

def valid_input():
    data = valid_output()
    data.pop("fields")
    return data

class TestDisplayModel:
    def test_valid_output(self):
        try:
            obj = DisplayModel(**valid_output())
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
            DisplayModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_project_id_invalid_types(self, value):
        data = valid_output()
        data["project_id"] = value
        with pytest.raises(ValidationError):
            DisplayModel(**data)
            
    ####  index_pattern  #######################################################
            
    def test_output_index_pattern_invalid_missing(self):
        data = valid_output()
        data.pop("index_pattern")
        with pytest.raises(ValidationError):
            DisplayModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_index_pattern_invalid_types(self, value):
        data = valid_output()
        data["index_pattern"] = value
        with pytest.raises(ValidationError):
            DisplayModel(**data)
            
    ####  fields  ##############################################################
            
    def test_output_fields_valid_missing(self):
        data = valid_output()
        data.pop("fields")
        DisplayModel(**data)
            
    @pytest.mark.parametrize("value", [0, True, False, [1], [{}], {} ])
    def test_output_fields_invalid_types(self, value):
        data = valid_output()
        data["fields"] = value
        with pytest.raises(ValidationError):
            DisplayModel(**data)
            
    ####  template  ############################################################
            
    def test_output_template_valid_missing(self):
        data = valid_output()
        data.pop("template")
        DisplayModel(**data)