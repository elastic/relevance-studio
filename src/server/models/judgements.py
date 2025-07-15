# Standard packages
from typing import List

# Third-party packages
from pydantic import Field, field_validator

# App packages
from .asset import AssetCreate, AssetUpdate

class JudgementCreate(AssetCreate):
    
    # Required inputs
    project_id: str
    scenario_id: str
    index: str
    doc_id: str
    rating: int = Field(ge=0)

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str):
        if not value.strip():
            raise ValueError("project_id must be a non-empty string")
        return value

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str):
        if not value.strip():
            raise ValueError("scenario_id must be a non-empty string")
        return value

    @field_validator("index")
    @classmethod
    def validate_index(cls, value: str):
        if not value.strip():
            raise ValueError("index must be a non-empty string")
        return value

    @field_validator("doc_id")
    @classmethod
    def validate_doc_id(cls, value: str):
        if not value.strip():
            raise ValueError("doc_id must be a non-empty string")
        return value

    @field_validator("rating", mode="before")
    @classmethod
    def validate_rating(cls, value: int):
        if isinstance(value, bool):
            raise ValueError("rating must be an integer")
        return value
    
class JudgementUpdate(AssetUpdate):
    """
    The Judgements API doesn't support partial updates.
    """
    def __init__(self, *args, **kwargs):
        raise Exception("Not implemented.")