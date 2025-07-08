# Standard packages
from __future__ import annotations
from typing import List, Optional

# Third-party packages
from pydantic import BaseModel, Field, model_validator, ValidationInfo

# App packages
from .asset import AssetModel

class BenchmarkModel(AssetModel):
    project_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default_factory=list)
    task: Optional[TaskModel] = None
    
    @model_validator(mode="after")
    def validate_params(self, info: ValidationInfo) -> BenchmarkModel:
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
            if self.tags and not all(isinstance(t, str) and t.strip() for t in self.tags):
                raise ValueError("tags must have non-empty strings")
        else:
            if self.task and 'k' in self.task.model_fields_set:
                raise ValueError("task.k is immutable")
        return self

class TaskStrategiesModel(BaseModel):
    ids_: Optional[List[str]] = Field(alias="_ids", default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)

class TaskScenariosModel(BaseModel):
    ids_: Optional[List[str]] = Field(alias="_ids", default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    sample_size: Optional[int] = Field(default=1000)
    sample_seed: Optional[str] = Field(default=None)
    
class TaskModel(BaseModel):
    metrics: List[str] = Field(default_factory=lambda: ["ndcg", "precision", "recall"])
    k: int = 10
    strategies: TaskStrategiesModel = Field(default_factory=TaskStrategiesModel)
    scenarios: TaskScenariosModel = Field(default_factory=TaskScenariosModel)