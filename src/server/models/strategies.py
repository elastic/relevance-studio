# Standard packages
from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional

# Third-party packages
from pydantic import Field, model_validator, ValidationInfo

# App packages
from .asset import AssetModel
from .. import utils

RE_ISO_8601_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

class StrategyModel(AssetModel):
    project_id: Optional[str] = None
    name: Optional[str] = None
    params: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    template: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode="after")
    def validate_params(self, info: ValidationInfo) -> StrategyModel:
        """
        Check for required fields differently in creates and updates.
        """
        context = info.context or {}
        is_partial = context.get("is_partial", False)
        if not is_partial:
            if not self.project_id:
                raise ValueError("project_id is required")
            if not self.name:
                raise ValueError("name is required")
            if not self.template:
                raise ValueError("template is required")
            if self.params and not all(isinstance(p, str) and p.strip() for p in self.params):
                raise ValueError("params must have non-empty strings")
            if self.tags and not all(isinstance(t, str) and t.strip() for t in self.tags):
                raise ValueError("tags must have non-empty strings")
        return self
    
    @model_validator(mode='before')
    @classmethod
    def validate_params_template_consistency(cls, data):
        """
        Ensure template.source is serialized as a JSON sttring.
        Ensure that params and template are consistent.
        """
        if isinstance(data, dict):
            # Serialize template.source if it's a dict
            template = data.get("template")
            if isinstance(template, dict) and isinstance(template.get("source"), dict):
                template["source"] = json.dumps(template["source"])
            
            # Reject case where template is explicitly None and params is given
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
        print(self.template)
        template_source = self.template.get("source")
        if not template_source:
            return
        expected = utils.extract_params(template_source)
        if self.params == []:
            self.params = expected
        elif self.params != expected:
            raise ValueError(f"`params` must match mustache variables in `template`. Expected {expected}, got {self.params}")