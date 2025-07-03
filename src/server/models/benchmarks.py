# Standard packages
from __future__ import annotations
from typing import List, Optional

# Third-party packages
from pydantic import BaseModel, Field

class BenchmarkModel(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default_factory=list)
    task: TaskModel

class TaskStrategiesModel(BaseModel):
    ids_: Optional[List[str]] = Field(alias="_ids", default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)

class TaskScenariosModel(BaseModel):
    ids_: Optional[List[str]] = Field(alias="_ids", default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    sample_size: Optional[int] = Field(default=1000)
    sample_seed: Optional[str] = Field(default=None)
    
class TaskModel(BaseModel):
    metrics: List[str]
    k: int
    strategies: TaskStrategiesModel = Field(default_factory=TaskStrategiesModel)
    scenarios: TaskScenariosModel = Field(default_factory=TaskScenariosModel)