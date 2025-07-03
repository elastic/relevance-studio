# Standard packages
from __future__ import annotations
from typing import List

# Third-party packages
from pydantic import BaseModel, Field, model_validator

class ProjectModel(BaseModel):
    name: str
    index_pattern: str
    params: List[str]
    rating_scale: RatingScaleModel
    
    @model_validator(mode="after")
    def validate_params(self) -> ProjectModel:
        if not self.params or not all(isinstance(p, str) and p.strip() for p in self.params):
            raise ValueError("params must be a non-empty list of non-empty strings")
        return self
    
class RatingScaleModel(BaseModel):
    min: int = Field(ge=0)
    max: int = Field(ge=1)
    
    @model_validator(mode="after")
    def validate_min_max(self) -> RatingScaleModel:
        if self.max <= self.min:
            raise ValueError("rating_scale.max must be greater than rating_scale.min")
        return self

    @model_validator(mode="before")
    @classmethod
    def invalidate_bools(cls, data):
        if not isinstance(data, dict):
            return data
        for field in ("min", "max"):
            if isinstance(data.get(field), bool):
                raise ValueError(f"{field} must not be a boolean")
        return data