# Third-party packages
import pytest
from pydantic import ValidationError

# App packages
from server.models.projects import ProjectModel, RatingScaleModel
from tests.utils import is_equal

def valid_doc():
    data = {
        "name": "Products",
        "index_pattern": "products",
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 4 },
    }
    return data

class TestProjectModel:
    def test_valid_instance(self):
        try:
            obj = ProjectModel(**valid_doc())
            is_equal(obj.model_dump(by_alias=True), valid_doc())
            assert isinstance(obj.rating_scale, RatingScaleModel)
        except Exception as e:
            pytest.fail(f"Unexpected error during instantiation: {e}")
            
    ####  name  ################################################################
            
    def test_doc_name_invalid_missing(self):
        data = valid_doc()
        data.pop("name")
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_name_invalid_types(self, value):
        data = valid_doc()
        data["name"] = value
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    ####  index_pattern  #######################################################
            
    def test_doc_index_pattern_invalid_missing(self):
        data = valid_doc()
        data.pop("index_pattern")
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], {} ])
    def test_doc_index_pattern_invalid_types(self, value):
        data = valid_doc()
        data["index_pattern"] = value
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    ####  params  ##############################################################
            
    def test_doc_params_valid_missing(self):
        data = valid_doc()
        data.pop("params")
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [[], [""]])
    def test_doc_params_invalid_empty(self, value):
        data = valid_doc()
        data["params"] = value
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [0, None, True, False, [1], [{}], {} ])
    def test_doc_params_invalid_types(self, value):
        data = valid_doc()
        data["params"] = value
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    ####  rating_scale  ########################################################
            
    def test_doc_rating_scale_invalid_missing(self):
        data = valid_doc()
        data.pop("rating_scale")
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [0, "zero", None, True, False, [{"min":0,"max":4}]])
    def test_doc_rating_scale_invalid_types(self, value):
        data = valid_doc()
        data["rating_scale"] = value
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    def test_doc_rating_scale_invalid_range(self):
        data = valid_doc()
        data["rating_scale"]["min"] = 2
        data["rating_scale"]["max"] = 1
        with pytest.raises(ValidationError):
            ProjectModel(**data)
    
    ####  rating_scale.min  ####################################################
            
    def test_doc_rating_scale_min_invalid_missing(self):
        data = valid_doc()
        data["rating_scale"].pop("min")
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [-1, 3.14, "one", None, True, False, [1], {}])
    def test_doc_rating_scale_min_invalid_types(self, value):
        data = valid_doc()
        data["rating_scale"]["min"] = value
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [0, 1, 2])
    def test_doc_rating_scale_min_valid_types(self, value):
        data = valid_doc()
        data["rating_scale"]["min"] = value
        obj = ProjectModel(**data)
        assert obj.rating_scale.min == value
            
    ####  rating_scale.max  ####################################################
            
    def test_doc_rating_scale_max_invalid_missing(self):
        data = valid_doc()
        data["rating_scale"].pop("max")
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [-1, 0, 3.14, "one", None, True, False, [1], {}])
    def test_doc_rating_scale_max_invalid_types(self, value):
        data = valid_doc()
        data["rating_scale"]["max"] = value
        with pytest.raises(ValidationError):
            ProjectModel(**data)
            
    @pytest.mark.parametrize("value", [1, 2, 3])
    def test_doc_rating_scale_max_valid_types(self, value):
        data = valid_doc()
        data["rating_scale"]["max"] = value
        obj = ProjectModel(**data)
        assert obj.rating_scale.max == value