# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.benchmarks import BenchmarkModel
from tests.utils import is_equal

def valid_doc():
    data = {
        "project_id": "58278355-f4f3-56d2-aa81-498250f27798",
        "name": "Product Search",
        "description": "Determine which strategy delivers the best search experience for our product catalog.",
        "tags": [
            "bm25",
            "elser",
            "signals"
        ],
        "task": {
            "metrics": [
                "ndcg",
                "precision",
                "recall"
            ],
            "k": 10,
            "strategies": {
                "tags": [
                    "bm25",
                    "elser",
                    "signals"
                ]
            },
            "scenarios": {
                "sample_size": 1000
            }
        }
    }
    return data

class TestBenchmarkModel:
    def test_valid_instance(self):
        try:
            obj = BenchmarkModel(**valid_doc())
            assert is_equal(obj.model_dump(by_alias=True, mode="json", exclude_none=True, exclude_unset=True), valid_doc())
        except Exception as e:
            pytest.fail(f"Unexpected error during instantiation: {e}")
            
    ####  project_id  ##########################################################
            
    def test_doc_project_id_invalid_missing(self):
        data = valid_doc()
        data.pop("project_id")
        with pytest.raises(ValidationError):
            BenchmarkModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_project_id_invalid_types(self, value):
        data = valid_doc()
        data["project_id"] = value
        with pytest.raises(ValidationError):
            BenchmarkModel(**data)
            
    ####  name  ################################################################
            
    def test_doc_name_invalid_missing(self):
        data = valid_doc()
        data.pop("name")
        with pytest.raises(ValidationError):
            BenchmarkModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_name_invalid_types(self, value):
        data = valid_doc()
        data["name"] = value
        with pytest.raises(ValidationError):
            BenchmarkModel(**data)
            
    ####  description  #########################################################
            
    def test_doc_description_valid_missing(self):
        data = valid_doc()
        data.pop("description")
        BenchmarkModel(**data)
            
    @pytest.mark.parametrize("value", [0, True, False, [1], {} ])
    def test_doc_description_invalid_types(self, value):
        data = valid_doc()
        data["description"] = value
        with pytest.raises(ValidationError):
            BenchmarkModel(**data)
            
    ####  tags  ################################################################
            
    def test_doc_tags_valid_missing(self):
        data = valid_doc()
        data.pop("tags")
        BenchmarkModel(**data)
            
    @pytest.mark.parametrize("value", [None, []])
    def test_doc_tags_valid_types(self, value):
        data = valid_doc()
        data["tags"] = value
        BenchmarkModel(**data)
            
    @pytest.mark.parametrize("value", [0, "body", True, False, [1], [{}], {} ])
    def test_doc_tags_invalid_types(self, value):
        data = valid_doc()
        data["tags"] = value
        with pytest.raises(ValidationError):
            BenchmarkModel(**data)