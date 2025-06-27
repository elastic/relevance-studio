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
        """
        if self.params or not self.values:
            return
        self.params = list(self.values.keys())