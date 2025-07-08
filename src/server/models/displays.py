# Standard packages
from __future__ import annotations
from typing import Any, List, Optional

# Third-party packages
from pydantic import Field, model_validator, ValidationInfo

# App packages
from .asset import AssetModel
from .. import utils

class DisplayModel(AssetModel):
    project_id: Optional[str] = None
    index_pattern: Optional[str] = None
    fields: Optional[List[str]] = Field(default_factory=list)
    template: Optional[Any] = Field(default_factory=dict)
    
    @model_validator(mode="after")
    def validate_params(self, info: ValidationInfo) -> DisplayModel:
        """
        Check for required fields differently in creates and updates.
        """
        context = info.context or {}
        is_partial = context.get("is_partial", False)
        if not is_partial:
            if not self.project_id:
                raise ValueError("project_id is required")
            if not self.index_pattern:
                raise ValueError("index_pattern is required")
            if not all(isinstance(f, str) and f.strip() for f in self.fields):
                raise ValueError("fields must have non-empty strings")
        return self
    
    def model_post_init(self, __context):
        """
        Extract params from the template body if params was not given.
        Exclude params that don't exist in mappings, such as _id.
        """
        self.fields = []
        template_body = self.template.get("body")
        if template_body:
            params = utils.extract_params(template_body)
            self.fields += [ p for p in params if not p.startswith("_") ]
        template_image = self.template.get("image", {}).get("url")
        if template_image:
            params = utils.extract_params(template_image)
            self.fields += [ p for p in params if not p.startswith("_") ]
        # Dedupe and sort
        self.fields = sorted(list(dict.fromkeys(self.fields)))