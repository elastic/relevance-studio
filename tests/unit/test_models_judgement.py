# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.judgements import JudgementModel
from tests.utils import is_equal

def valid_doc():
    data = {
        "@timestamp": "2025-07-02T16:41:54.672797Z",
        "@author": "human",
        "project_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "scenario_id": "5199e0ae-de59-5227-9647-c44f2c6617fc",
        "index": "products",
        "doc_id": "41476",
        "rating": 3
    }
    return data

def valid_input():
    data = valid_doc()
    data.pop("@timestamp")
    return data

class TestJudgementModel:
    def test_valid_instance(self):
        try:
            obj = JudgementModel(**valid_doc())
            assert is_equal(obj.model_dump(by_alias=True), valid_doc())
        except Exception as e:
            pytest.fail(f"Unexpected error during instantiation: {e}")
            
    ####  @timestamp  ##########################################################
            
    def test_doc_timestamp_valid_missing(self):
        data = valid_doc()
        data.pop("@timestamp")
        JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_timestamp_invalid_types(self, value):
        data = valid_doc()
        data["@timestamp"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [
        "2025-07-02",                         # date only
        "2025-07-02 16:41:54",                # space instead of T
        "2025-07-02T16:41:54",                # missing Z
        "2025/07/02T16:41:54.123456Z",        # wrong date separator
        "07-02-2025T16:41:54.123456Z",        # wrong order
        "2025-07-02T16:41:54.123456+00:00",   # offset instead of Z
        ""
    ])
    def test_doc_timestamp_invalid_format(self, value):
        data = valid_doc()
        data["@timestamp"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  @author  #############################################################
            
    def test_doc_author_valid_missing(self):
        data = valid_doc()
        data.pop("@author")
        JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_author_invalid_types(self, value):
        data = valid_doc()
        data["@author"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    def test_input_author_valid_default(self):
        data = valid_input()
        obj = JudgementModel(**data)
        assert obj.author_ == "human"
            
    ####  project_id  ##########################################################
            
    def test_doc_project_id_invalid_missing(self):
        data = valid_doc()
        data.pop("project_id")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_project_id_invalid_types(self, value):
        data = valid_doc()
        data["project_id"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  scenario_id  #########################################################
            
    def test_doc_scenario_id_invalid_missing(self):
        data = valid_doc()
        data.pop("scenario_id")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_scenario_id_invalid_types(self, value):
        data = valid_doc()
        data["scenario_id"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  doc_id  ##############################################################
            
    def test_doc_doc_id_invalid_missing(self):
        data = valid_doc()
        data.pop("doc_id")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_doc_id_invalid_types(self, value):
        data = valid_doc()
        data["doc_id"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  index  ###############################################################
            
    def test_doc_index_invalid_missing(self):
        data = valid_doc()
        data.pop("index")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_index_invalid_types(self, value):
        data = valid_doc()
        data["index"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    ####  rating  ##############################################################
            
    def test_doc_rating_invalid_missing(self):
        data = valid_doc()
        data.pop("rating")
        with pytest.raises(ValidationError):
            JudgementModel(**data)
            
    @pytest.mark.parametrize("value", [-1, "one", None, True, False, [1], {} ])
    def test_doc_rating_invalid_types(self, value):
        data = valid_doc()
        data["rating"] = value
        with pytest.raises(ValidationError):
            JudgementModel(**data)