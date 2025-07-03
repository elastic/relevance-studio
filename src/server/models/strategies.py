# Standard packages
import re
from typing import Any, Dict, List, Optional

# Third-party packages
from pydantic import BaseModel, Field, model_validator

# App packages
from .. import utils

RE_ISO_8601_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

class StrategyModel(BaseModel):
    timestamp_: Optional[str] = Field(alias='@timestamp', default=None)
    project_id: str
    name: str
    params: Optional[List[str]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    template: Optional[Dict[str, Any]] = Field(default=None)
    
    @model_validator(mode='before')
    @classmethod
    def validate_params_template_consistency(cls, data):
        """Validate that params and template are consistent"""
        if isinstance(data, dict):
            # If template key exists and is None, but params is provided, that's invalid
            if 'template' in data and data['template'] is None and data.get('params') is not None:
                raise ValueError("Cannot specify `params` when `template` is explicitly None")
        return data
    
    def model_post_init(self, __context):
        """
        Extract params from the template if params was not given.
        Ensure the params match the keys of values.
        """
        if not self.template:
            return
        template_source = self.template.get("source")
        if not template_source:
            return    
        expected = utils.extract_params(template_source)
        if self.params is None:
            self.params = expected
        elif self.params != expected:
            raise ValueError(f"`params` must match mustache variables in `template`. Expected {expected}, got {self.params}")
    
    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
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