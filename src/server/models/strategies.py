# Standard packages
from typing import List, Optional, ClassVar

# Third-party packages
from pydantic import BaseModel, computed_field, Field, field_validator

# App packages
from .asset import AssetCreate, AssetUpdate
from .. import utils

class TemplateCreate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    lang: str = "mustache"
    source: str = ""

class TemplateUpdate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    lang: Optional[str] = None
    source: Optional[str] = None

class StrategyCreate(AssetCreate):
    asset_type: ClassVar[str] = "strategies"
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
        if not self.template or not self.template.source:
            return []
        # Pass the source string directly without JSON serialization
        return utils.extract_params(self.template.source)    
class StrategyUpdate(AssetUpdate):
    
    asset_type: ClassVar[str] = "strategies"
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
        if not self.template or not hasattr(self.template, 'source') or self.template.source is None:
            return None
        # Pass the source string directly without JSON serialization
        return utils.extract_params(self.template.source)