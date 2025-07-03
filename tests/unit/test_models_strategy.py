# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.strategies import StrategyModel
from tests.utils import is_equal

def valid_doc():
    data = {
        "@timestamp": "2025-07-02T16:41:58.137693Z",
        "project_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "name": "Classical - Name match",
        "params": [
            "text"
        ],
        "tags": [
            "bm25"
        ],
        "template": {
            "source": {
                "retriever": {
                    "standard": {
                        "query": {
                            "match": {
                                "name.text": {
                                    "query": "{{ text }}"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return data

def valid_input():
    data = valid_doc()
    data.pop("params")
    return data

class TestStrategyModel:
    def test_valid_instance(self):
        try:
            obj = StrategyModel(**valid_doc())
            assert is_equal(obj.model_dump(by_alias=True), valid_doc())
        except Exception as e:
            pytest.fail(f"Unexpected error during instantiation: {e}")
            
    ####  @timestamp  ##########################################################
            
    def test_doc_timestamp_valid_missing(self):
        data = valid_doc()
        data.pop("@timestamp")
        StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_timestamp_invalid_types(self, value):
        data = valid_doc()
        data["@timestamp"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
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
            StrategyModel(**data)
            
    ####  project_id  ##########################################################
            
    def test_doc_project_id_invalid_missing(self):
        data = valid_doc()
        data.pop("project_id")
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_project_id_invalid_types(self, value):
        data = valid_doc()
        data["project_id"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    ####  name  ################################################################
            
    def test_doc_name_invalid_missing(self):
        data = valid_doc()
        data.pop("name")
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_name_invalid_types(self, value):
        data = valid_doc()
        data["name"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    ####  params  ##############################################################
    
    def test_doc_params_must_match_values(self):
        data = valid_doc()
        data["params"] = ["text", "wrong"]
        with pytest.raises(ValueError):
            StrategyModel(**data)

    def test_doc_params_none_template_none_valid(self):
        data = valid_doc()
        data["template"] = None
        data["params"] = None
        StrategyModel(**data)

    def test_doc_params_nonempty_template_none_invalid(self):
        data = valid_doc()
        data["template"] = None
        data["params"] = ["text"]
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    ####  tags  ################################################################
            
    def test_doc_tags_valid_missing(self):
        data = valid_doc()
        data.pop("tags")
        StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [None, []])
    def test_doc_tags_valid_types(self, value):
        data = valid_doc()
        data["tags"] = value
        StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, "body", True, False, [1], [{}], {} ])
    def test_doc_tags_invalid_types(self, value):
        data = valid_doc()
        data["tags"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)
            
    ####  template  ############################################################
            
    def test_doc_template_valid_missing(self):
        data = valid_doc()
        data.pop("template")
        StrategyModel(**data)
            
    @pytest.mark.parametrize("value", [0, "body", True, False, [1], [{}] ])
    def test_doc_template_invalid_types(self, value):
        data = valid_doc()
        data["template"] = value
        with pytest.raises(ValidationError):
            StrategyModel(**data)