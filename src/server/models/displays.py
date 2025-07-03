# Standard packages
from __future__ import annotations
from typing import Any, List, Optional

# Third-party packages
from pydantic import BaseModel, Field, model_validator

# App packages
from .. import utils

class DisplayModel(BaseModel):
    project_id: str
    index_pattern: str
    fields: Optional[List[str]] = Field(default_factory=list)
    template: Optional[Any] = Field(default=None)
    
    def model_post_init(self, __context):
        """
        Extract params from the template body if params was not given.
        Exclude params that don't exist in mappings, such as _id.
        """
        if self.fields:
            return
        if not self.template:
            return
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