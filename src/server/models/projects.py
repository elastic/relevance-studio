# Standard packages
from typing import List

# Third-party packages
from pydantic import BaseModel

class RatingScaleModel(BaseModel):
    min: int = 0
    max: int

class ProjectModel(BaseModel):
    name: str
    index_pattern: str
    params: List[str]
    rating_scale: RatingScaleModel