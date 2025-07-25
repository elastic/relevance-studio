# Standard packages
from typing import Any, Dict, List, Optional

# Third-party packages
from pydantic import BaseModel, Field, field_validator, model_validator, StrictInt

# App packages
from .asset import AssetCreate, AssetUpdate


class TaskStrategiesCreate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    ids_: List[str] = Field(alias="_ids", default_factory=list)
    tags: List[str] = Field(default_factory=list)
    docs: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("ids_")
    @classmethod
    def validate_ids(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("_ids must be a list of non-empty strings if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value

    @field_validator("docs")
    @classmethod
    def validate_docs(cls, value: List[Dict[str, Any]]):
        if not isinstance(value, list) or not all(isinstance(d, dict) for d in value):
            raise ValueError("docs must be a list of objects if given")
        return value

class TaskStrategiesUpdate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    ids_: List[str] = Field(alias="_ids", default_factory=list)
    tags: List[str] = Field(default_factory=list)
    docs: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("ids_")
    @classmethod
    def validate_ids(cls, value: List[str]):
        if value is None:
            return value
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("_ids must be a list of non-empty strings if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if value is None:
            return value
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags ust be a list of non-empty strings if given")
        return value

    @field_validator("docs")
    @classmethod
    def validate_docs(cls, value: List[Dict[str, Any]]):
        if not isinstance(value, list) or not all(isinstance(d, dict) for d in value):
            raise ValueError("docs must be a list of objects if given")
        return value

class TaskScenariosCreate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    ids_: List[str] = Field(alias="_ids", default_factory=list)
    tags: List[str] = Field(default_factory=list)
    sample_size: Optional[StrictInt] = Field(default=1000, ge=1)
    sample_seed: Optional[str] = Field(default=None)

    @field_validator("ids_")
    @classmethod
    def validate_ids(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("_ids must be a list of non-empty strings if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value
    
    @field_validator("sample_size", mode="before")
    @classmethod
    def validate_sample_size(cls, value):
        if value is None or isinstance(value, bool):
            raise ValueError("sample_size must be an integer")
        return value

class TaskScenariosUpdate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    ids_: List[str] = Field(alias="_ids", default_factory=list)
    tags: List[str] = Field(default_factory=list)
    sample_size: Optional[StrictInt] = Field(default=1000, ge=1)
    sample_seed: Optional[str] = Field(default=None)

    @field_validator("ids_")
    @classmethod
    def validate_ids(cls, value: List[str]):
        if value is None:
            return value
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("_ids must be a list of non-empty strings if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if value is None:
            return value
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value
    
    @field_validator("sample_size", mode="before")
    @classmethod
    def validate_sample_size(cls, value):
        if value is None or isinstance(value, bool):
            raise ValueError("sample_size must be an integer")
        return value

class TaskCreate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    metrics: List[str] = Field(default_factory=lambda: ["ndcg", "precision", "recall"])
    k: StrictInt = Field(default=10, ge=1)
    strategies: TaskStrategiesCreate = Field(default_factory=TaskStrategiesCreate)
    scenarios: TaskScenariosCreate = Field(default_factory=TaskScenariosCreate)

    @field_validator("k", mode="before")
    @classmethod
    def validate_k(cls, value):
        if isinstance(value, bool):
            raise ValueError("k must be an integer")
        return value

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, value: List[str]):
        if not value:
            raise ValueError("metrics must have at least one value")
        stripped = [m.strip() for m in value if isinstance(m, str)]
        if len(stripped) != len(value) or not all(stripped):
            raise ValueError("metrics must be a list of non-empty strings")
        return stripped

class TaskUpdate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    metrics: Optional[List[str]] = None
    strategies: Optional[TaskStrategiesUpdate] = None
    scenarios: Optional[TaskScenariosUpdate] = None

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, value: List[str]):
        if not value:
            raise ValueError("metrics must have at least one value")
        stripped = [m.strip() for m in value if isinstance(m, str)]
        if len(stripped) != len(value) or not all(stripped):
            raise ValueError("metrics must be a list of non-empty strings")
        return stripped

    @model_validator(mode="before")
    @classmethod
    def forbid_k(cls, data):
        if "k" in data:
            raise ValueError("task.k is immutable and cannot be updated")
        return data

class BenchmarkCreate(AssetCreate):

    # Required inputs
    workspace_id: str
    name: str

    # Optional inputs
    task: Optional[TaskCreate] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, value: str):
        if not value.strip():
            raise ValueError("workspace_id must be a non-empty string")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        if not value.strip():
            raise ValueError("name must be a non-empty string")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value
    
    @model_validator(mode="before")
    @classmethod
    def validate_task(cls, data):
        if "task" not in data:
            data["task"] = TaskCreate()
        elif data["task"] is None:
            raise ValueError("task must be an object if given")
        return data

class BenchmarkUpdate(AssetUpdate):

    # Required inputs
    workspace_id: str

    # Optional inputs
    name: str = None
    description: str = None
    tags: Optional[List[str]] = None
    task: Optional[TaskUpdate] = None

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, value: str):
        if not value.strip():
            raise ValueError("workspace_id must be a non-empty string")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]):
        if value is None:
            return value
        if not value.strip():
            raise ValueError("name must be a non-empty string if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if value is None or not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value