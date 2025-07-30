# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

# Standard packages
from typing import List, Optional

# Third-party packages
from pydantic import BaseModel, Field, field_validator, StrictInt

# App packages
from .asset import AssetCreate, AssetUpdate

class RatingScaleModel(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Required inputs
    min: StrictInt = Field(ge=0)
    max: StrictInt = Field(ge=1)

    @field_validator("min", mode="before")
    @classmethod
    def validate_min(cls, value):
        if isinstance(value, bool):
            raise ValueError("rating_scale.min must be an integer")
        return value
    
    @field_validator("max", mode="before")
    @classmethod
    def validate_max(cls, value):
        if isinstance(value, bool):
            raise ValueError("rating_scale.max must be an integer")
        return value

    @field_validator("max")
    @classmethod
    def validate_max_is_greater_than_min(cls, max_value, info):
        min_value = info.data.get("min")
        if min_value is not None and max_value <= min_value:
            raise ValueError("rating_scale.max must be greater than rating_scale.min")
        return max_value

class WorkspaceCreate(AssetCreate):
    
    # Required inputs
    name: str
    index_pattern: str
    params: List[str]
    rating_scale: RatingScaleModel
    
    # Optional inputs
    tags: List[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        if not value.strip():
            raise ValueError("name must be a non-empty string")
        return value

    @field_validator("index_pattern")
    @classmethod
    def validate_index_pattern(cls, value: str):
        if not value.strip():
            raise ValueError("index_pattern must be a non-empty string")
        return value

    @field_validator("params")
    @classmethod
    def validate_params(cls, value: List[str]):
        if not value or not all(isinstance(p, str) and p.strip() for p in value):
            raise ValueError("params must be a non-empty list of non-empty strings")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value


class WorkspaceUpdate(AssetUpdate):
    
    # Optional inputs
    name: str = None
    index_pattern: str = None
    params: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]):
        if value is None:
            return value
        if not value.strip():
            raise ValueError("name must be a non-empty string if given")
        return value

    @field_validator("index_pattern")
    @classmethod
    def validate_index_pattern(cls, value: Optional[str]):
        if value is None:
            return value
        if not value.strip():
            raise ValueError("index_pattern must be a non-empty string if given")
        return value

    @field_validator("params")
    @classmethod
    def validate_params(cls, value: Optional[List[str]]):
        if value is None:
            return value
        if not all(isinstance(p, str) and p.strip() for p in value):
            raise ValueError("params must be a non-empty list of non-empty strings if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if value is None or not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value