# Standard packages
from typing import Any, Dict, List, Optional

# Third-party packages
from pydantic import BaseModel, Field

# App packages
from .. import utils

class StrategyModel(BaseModel):
    timestamp_: Optional[str] = Field(alias='@timestamp', default=None)
    project_id: str
    name: str
    params: Optional[List[str]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    template: Optional[Dict[str, Any]] = Field(default=None)
    
    def model_post_init(self, __context):
        """
        Extract params from the template if params was not given.
        """
        print(self)
        if self.params or not self.template:
            return     
        template_source = self.template.get("source")
        if template_source:
            self.params = utils.extract_params(template_source)