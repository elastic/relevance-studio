# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import re
from typing import Any, Dict, Optional

# Third-party packages
from pydantic import BaseModel, Field, model_validator, ValidationInfo

# App packages
from .. import utils

RE_ISO_8601_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

def is_valid_timestamp(ts):
    return RE_ISO_8601_TIMESTAMP.match(ts)

class Asset(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    meta: Dict[str, Optional[str]] = Field(alias='@meta')
    
    @classmethod
    def model_input_json_schema(cls, **kwargs: Any) -> dict:
        """
        Return the JSON schema for inputs, which excludes the @meta field. 
        """
        schema = super().model_json_schema(**kwargs)
        if "properties" in schema:
            schema["properties"].pop("@meta", None)
        if "required" in schema and "@meta" in schema["required"]:
            schema["required"].remove("@meta")
        return schema

class AssetCreate(Asset):

    @model_validator(mode="before")
    @classmethod
    def enrich_meta(cls, input: Dict[str, Any], info: ValidationInfo):
        user = (info.context or {}).get("user") or "unknown"
        if "@meta" in input:
            raise ValueError("@meta is forbidden as an input")
        input["@meta"] = {
            "created_at": utils.timestamp(),
            "created_by": user,
            "updated_at": None,
            "updated_by": None
        }
        return input

    @model_validator(mode="after")
    def validate_meta(self):
        if not is_valid_timestamp(self.meta.get("created_at")):
            raise ValueError("@meta.created_at at must be a valid ISO 8601 timestamp")
        if not self.meta.get("created_by"):
            raise ValueError("created_by is required")
        return self
    
    def serialize(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)

class AssetUpdate(Asset):

    @model_validator(mode="before")
    @classmethod
    def enrich_meta(cls, input: Dict[str, Any], info: ValidationInfo):
        user = (info.context or {}).get("user") or "unknown"
        if "@meta" in input:
            raise ValueError("@meta is forbidden as an input")
        input["@meta"] = {
            "updated_at": utils.timestamp(),
            "updated_by": user
        }
        return input

    @model_validator(mode="after")
    def validate_meta(self):
        if not is_valid_timestamp(self.meta.get("updated_at")):
            raise ValueError("@meta.updated_at at must be a valid ISO 8601 timestamp")
        if not self.meta.get("updated_by"):
            raise ValueError("updated_by is required")
        return self
    
    def serialize(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)