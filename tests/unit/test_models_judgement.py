# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.judgements import JudgementModel
from tests.utils import has_valid_meta_for_create, is_equal

def valid_output():
    data = {
        "project_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "scenario_id": "5199e0ae-de59-5227-9647-c44f2c6617fc",
        "index": "products",
        "doc_id": "41476",
        "rating": 3
    }
    return data

def valid_input():
    data = valid_output()
    data.pop("@timestamp")
    return data

class TestJudgementModel:
    def test_valid_output(self):
        try:
            obj = JudgementModel(**valid_output())
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
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_project_id_invalid_types(self, value):
        data = valid_output()
        data["project_id"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  scenario_id  #########################################################
            
    def test_output_scenario_id_invalid_missing(self):
        data = valid_output()
        data.pop("scenario_id")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_scenario_id_invalid_types(self, value):
        data = valid_output()
        data["scenario_id"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  doc_id  ##############################################################
            
    def test_output_doc_id_invalid_missing(self):
        data = valid_output()
        data.pop("doc_id")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_doc_id_invalid_types(self, value):
        data = valid_output()
        data["doc_id"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  index  ###############################################################
            
    def test_output_index_invalid_missing(self):
        data = valid_output()
        data.pop("index")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_output_index_invalid_types(self, value):
        data = valid_output()
        data["index"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  rating  ##############################################################
            
    def test_output_rating_invalid_missing(self):
        data = valid_output()
        data.pop("rating")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [-1, "one", None, True, False, [1], {} ])
    def test_output_rating_invalid_types(self, value):
        data = valid_output()
        data["rating"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)