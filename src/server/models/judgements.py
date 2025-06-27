# Standard packages
from typing import Optional

# Third-party packages
from pydantic import BaseModel, Field

class JudgementModel(BaseModel):
    timestamp_: Optional[str] = Field(alias='@timestamp', default=None)
    author: Optional[str] = Field(alias='@author', default="human")
    project_id: str
    scenario_id: str
    index: str
    doc_id: str
    rating: int