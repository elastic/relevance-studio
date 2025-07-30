# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

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

class DisplayCreate(AssetCreate):
    
    # Required inputs
    workspace_id: str
    index_pattern: str
    
    # Optional inputs
    template: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, value: str):
        if not value.strip():
            raise ValueError("workspace_id must be a non-empty string")
        return value

    @field_validator("index_pattern")
    @classmethod
    def validate_index_pattern(cls, value: Optional[str]):
        if not value.strip():
            raise ValueError("index_pattern must be a non-empty string")
        return value

    @computed_field
    @property
    def fields(self) -> List[str]:
        return extract_fields_from_template(self.template or {})
    
class DisplayUpdate(AssetUpdate):
    
    # Required inputs
    workspace_id: str
    
    # Optional inputs
    index_pattern: str = Field(default=None)
    template: Optional[Dict[str, Any]] = None

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, value: str):
        if not value.strip():
            raise ValueError("workspace_id must be a non-empty string")
        return value

    @field_validator("index_pattern")
    @classmethod
    def validate_index_pattern(cls, value: Optional[str]):
        if value is None:
            return value
        if not value.strip():
            raise ValueError("index_pattern must be a non-empty string if given")
        return value
    
    @field_validator("template")
    @classmethod
    def validate_template(cls, value: Dict[str, Any]):
        if not isinstance(value, dict):
            raise ValueError("template must be an object if given")
        return value

    @computed_field
    @property
    def fields(self) -> Optional[List[str]]:
        if isinstance(self.template, dict):
            return extract_fields_from_template(self.template)
        return None