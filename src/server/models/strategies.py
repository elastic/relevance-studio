# Standard packages
from typing import List, Optional

# Third-party packages
from pydantic import BaseModel, computed_field, Field, field_validator

# App packages
from .asset import AssetCreate, AssetUpdate
from .. import utils

class TemplateCreate(BaseModel):
    model_config = { "extra": "forbid" }
    lang: str = "mustache"
    source: str = ""

class TemplateUpdate(BaseModel):
    model_config = { "extra": "forbid" }
    lang: Optional[str] = None
    source: Optional[str] = None

class StrategyCreate(AssetCreate):
    
    # Required inputs
    project_id: str
    name: str
    
    # Optional inputs
    tags: List[str] = Field(default_factory=list)
    template: TemplateCreate = Field(default_factory=TemplateCreate)

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str):
        if not value.strip():
            raise ValueError("project_id must be a non-empty string")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]):
        if not value.strip():
            raise ValueError("name must be a non-empty string")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value

    @computed_field
    @property
    def params(self) -> Optional[List[str]]:
        return utils.extract_params(self.template.source or "") if self.template else []
    
class StrategyUpdate(AssetUpdate):
    
    # Required inputs
    project_id: str
    
    # Optional inputs
    name: str = Field(default=None)
    tags: Optional[List[str]] = None
    template: Optional[TemplateUpdate] = None

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str):
        if not value.strip():
            raise ValueError("project_id must be a non-empty string")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]):
        if not value.strip():
            raise ValueError("name must be a non-empty string")
        return value
    
    @field_validator("template", mode="before")
    @classmethod
    def validate_template(cls, value):
        if value is None:
            raise ValueError("template must be an object if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if value is None or not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value

    @computed_field
    @property
    def params(self) -> Optional[List[str]]:
        return utils.extract_params(self.template.source or "") if self.template and self.template.source else None