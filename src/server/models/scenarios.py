# Standard packages
from typing import Any, Dict, List, Optional

# Third-party packages
from pydantic import BaseModel, Field

class ScenarioModel(BaseModel):
    timestamp_: Optional[str] = Field(alias='@timestamp', default=None)
    project_id: str
    name: str
    params: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    values: Optional[Dict[str, Any]] = Field(default=None)
    
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