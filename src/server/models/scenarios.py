# Standard packages
from typing import Any, Dict, List, Optional

# Third-party packages
from pydantic import computed_field, Field, field_validator

# App packages
from .asset import AssetCreate, AssetUpdate
from .. import utils

def extract_fields_from_template(template: Dict[str, Any]) -> List[str]:
    """
    Extract mustache variables from template.body and image.url,
    excluding reserved fields like _id that start with an underscore.
    """
    fields = []
    for key in ["body", "image.url"]:
        value = template
        for part in key.split("."):
            value = value.get(part, {}) if isinstance(value, dict) else None
        if isinstance(value, str):
            for field in utils.extract_params(value):
                field = field.strip()
                if field and not field.startswith("_"):
                    fields.append(field)
    return sorted(set(fields))

class ScenarioCreate(AssetCreate):
    
    # Required inputs
    workspace_id: str
    name: str
    values: Dict[str, Any]
    
    # Optional inputs
    tags: List[str] = Field(default_factory=list)

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, value: str):
        if not value.strip():
            raise ValueError("workspace_id must be a non-empty string")
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

    @field_validator("values")
    @classmethod
    def validate_values(cls, value: Dict[str, any]):
        if value == {}:
            raise ValueError("values must not be empty")
        return value

    @computed_field
    @property
    def params(self) -> Optional[List[str]]:
        if isinstance(self.values, dict):
            return sorted(list(self.values.keys()))
    
class ScenarioUpdate(AssetUpdate):
    
    # Required inputs
    workspace_id: str
    
    # Optional inputs
    name: str = Field(default=None)
    tags: Optional[List[str]] = None

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, value: str):
        if not value.strip():
            raise ValueError("workspace_id must be a non-empty string")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]):
        if not value.strip():
            raise ValueError("name must be a non-empty string if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if value is None or not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value