# Standard packages
from __future__ import annotations
from typing import List, Optional

# Third-party packages
from pydantic import BaseModel, Field, model_validator, ValidationInfo

# App packages
from .asset import AssetModel

class ProjectModel(AssetModel):
    name: Optional[str] = None
    index_pattern: Optional[str] = None
    params: Optional[List[str]] = None
    rating_scale: Optional[RatingScaleModel] = None
    
    @model_validator(mode="after")
    def validate_params(self, info: ValidationInfo) -> ProjectModel:
        """
        Check for required fields differently in creates and updates.
        """
        context = info.context or {}
        is_partial = context.get("is_partial", False)
        if not is_partial:
            if not self.name:
                raise ValueError("name is required")
            if not self.index_pattern:
                raise ValueError("index_pattern is required")
            if not self.params or not all(isinstance(p, str) and p.strip() for p in self.params):
                raise ValueError("params must be a non-empty list of non-empty strings")
            if not self.rating_scale:
                raise ValueError("rating_scale is required")
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