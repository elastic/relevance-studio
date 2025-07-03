# Standard packages
import re
from typing import Any, Optional

# Third-party packages
from pydantic import BaseModel, Field, field_validator, model_validator

RE_ISO_8601_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

class JudgementModel(BaseModel):
    timestamp_: Optional[str] = Field(alias='@timestamp', default_factory=lambda: None)
    author_: Optional[str] = Field(alias='@author', default="human")
    project_id: str
    scenario_id: str
    index: str
    doc_id: str
    rating: int = Field(ge=0)
    
    @field_validator('author_', mode='before')
    @classmethod
    def validate_author_not_none(cls, v):
        if v is None:
            raise ValueError("@autho` must not be None")
        return v

    @model_validator(mode="before")
    @classmethod
    def invalidate_bools(cls, data):
        if not isinstance(data, dict):
            return data
        if isinstance(data.get("rating"), bool):
            raise ValueError(f"rating must not be a boolean")
        return data
    
    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(data.get("rating"), bool):
            raise ValueError("rating must not be a boolean")
        if "@timestamp" in data and data["@timestamp"] is None:
            raise ValueError("@timestamp must not be None")
        if "@timestamp" in data and not isinstance(data["@timestamp"], str):
            raise ValueError("@timestamp must be a string if present")
        return data

    @model_validator(mode="before")
    @classmethod
    def validate_fields_not_bool_and_timestamp(cls, data):
        if isinstance(data.get("rating"), bool):
            raise ValueError("rating must not be a boolean")
        if "@timestamp" in data:
            ts = data["@timestamp"]
            if not isinstance(ts, str):
                raise ValueError("@timestamp must be a string")
            if not RE_ISO_8601_TIMESTAMP.match(ts):
                raise ValueError("@timestamp must match ISO 8601 format: YYYY-MM-DDTHH:MM:SS(.ffffff)?Z")
        return data