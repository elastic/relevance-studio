# Standard packages
from __future__ import annotations
from typing import Any, Dict, List, Optional

# Third-party packages
from pydantic import Field, model_validator, ValidationInfo

# App packages
from .asset import AssetModel

class ScenarioModel(AssetModel):
    project_id: Optional[str] = None
    name: Optional[str] = None
    params: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    values: Optional[Dict[str, Any]] = Field(default=None)
    
    @model_validator(mode="after")
    def validate_params(self, info: ValidationInfo) -> ScenarioModel:
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
            if not self.values:
                raise ValueError("values is required")
            if not self.params:
                raise ValueError("params is required")
            if self.params and not all(isinstance(p, str) and p.strip() for p in self.params):
                raise ValueError("fields must have non-empty strings")
            if self.tags and not all(isinstance(t, str) and t.strip() for t in self.tags):
                raise ValueError("tags must have non-empty strings")
        else:
            if self.values:
                raise ValueError("values cannot be updated")
            if self.params:
                raise ValueError("params cannot be updated")
        return self
    
    def model_post_init(self, __context):
        """
        Extract params from the values if params was not given.
        Ensure the params match the keys of values.
        """
        if self.values is None:
            if self.params:
                raise ValueError("If `values` is None, then `params` must also be empty or None")
            return

        expected_params = sorted(list(self.values.keys()))
        if not self.params:
            self.params = expected_params
        elif sorted(self.params) != expected_params:
            raise ValueError(
                f"`params` ({self.params}) does not match keys of `values` ({expected_params})"
            )