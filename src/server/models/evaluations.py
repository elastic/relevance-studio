# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict, List, Optional

# Third-party packages
from pydantic import BaseModel, Field, field_validator, model_validator, StrictInt

# App packages
from .asset import is_valid_timestamp
from .benchmarks import TaskCreate
from .. import utils

class Hit(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Required fields
    id_: str = Field(alias="_id")
    index_: str = Field(alias="_index")
    score_: Optional[float] = Field(alias="_score", default=None)
    ignored_: Optional[str] = Field(alias="_ignored", default=None)

    @field_validator("id_")
    @classmethod
    def validate_id(cls, value: str):
        if not value.strip():
            raise ValueError("_id must be a non-empty string")
        return value

    @field_validator("index_")
    @classmethod
    def validate_index(cls, value: str):
        if not value.strip():
            raise ValueError("_index must be a non-empty string")
        return value

    @field_validator("score_", mode="before")
    @classmethod
    def validate_score(cls, value):
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("_score must be a number")
        return float(value)

class RatedHit(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    hit: Hit
    rating: Optional[StrictInt] = Field(default=None, ge=0)
    
    @field_validator("rating", mode="before")
    @classmethod
    def validate_rating(cls, value):
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("rating must be an integer")
        if value < 0:
            raise ValueError("rating must be greater than 0")
        return value

class MetricsModel(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    dcg: Optional[float] = None
    err: Optional[float] = None
    mrr: Optional[float] = None
    ndcg: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None

    @field_validator("dcg", "err", "mrr", "ndcg", "precision", "recall", mode="before")
    @classmethod
    def validate_metric(cls, value, info):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{info.field_name} must be a number if given")
        return float(value)

class SearchResult(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    scenario_id: str
    metrics: MetricsModel
    hits: List[RatedHit]

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str):
        if not value.strip():
            raise ValueError("scenario_id must be a non-empty string")
        return value

class Results(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    strategy_id: str
    searches: List[SearchResult]

    @field_validator("strategy_id")
    @classmethod
    def validate_strategy_id(cls, value: str):
        if not value.strip():
            raise ValueError("strategy_id must be a non-empty string")
        return value

class Runtime(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    indices: Dict[str, Any]
    scenarios: Dict[str, Any]
    strategies: Dict[str, Any]
    judgements: Dict[str, Any]

class UnratedDocs(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    id_: str = Field(alias="_id")
    index_: str = Field(alias="_index")
    count: StrictInt = Field(ge=0)
    strategies: List[str]
    scenarios: List[str]

    @field_validator("id_")
    @classmethod
    def validate_id(cls, value: str):
        if not value.strip():
            raise ValueError("_id must be a non-empty string")
        return value

    @field_validator("index_")
    @classmethod
    def validate_index(cls, value: str):
        if not value.strip():
            raise ValueError("_index must be a non-empty string")
        return value
    
    @field_validator("count", mode="before")
    @classmethod
    def validate_count(cls, value):
        if value is None or isinstance(value, bool):
            raise ValueError("count must be an integer if given")
        return value

    @field_validator("scenarios")
    @classmethod
    def validate_scenarios(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("scenarios must be a list of non-empty strings")
        return value

    @field_validator("strategies")
    @classmethod
    def validate_strategies(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("strategies must be a list of non-empty strings")
        return value
    
class Evaluation(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    meta: Dict[str, Optional[str]] = Field(alias='@meta')
    
    @classmethod
    def model_input_json_schema(cls, **kwargs: Any) -> dict:
        """
        Return the JSON schema for inputs, which excludes the @meta field. 
        """
        schema = super().model_json_schema(**kwargs)
        if "properties" in schema:
            schema["properties"].pop("@meta", None)
        if "required" in schema and "@meta" in schema["required"]:
            schema["required"].remove("@meta")
        return schema

class EvaluationCreate(Evaluation):
    
    # Required fields
    workspace_id: str
    benchmark_id: str
    task: TaskCreate
    
    @model_validator(mode="before")
    @classmethod
    def enrich_meta(cls, input, info):
        user = (info.context or {}).get("user") or "unknown"
        if "@meta" in input:
            raise ValueError("@meta is forbidden as an input")
        input["@meta"] = {
            "status": "pending",
            "created_at": utils.timestamp(),
            "created_by": user,
            "started_at": None,
            "started_by": None,
            "stopped_at": None,
        }
        return input

    @model_validator(mode="after")
    def validate_meta(self):
        if not is_valid_timestamp(self.meta.get("created_at")):
            raise ValueError("@meta.created_at at must be a valid ISO 8601 timestamp")
        if not self.meta.get("created_by"):
            raise ValueError("created_by is required")
        return self

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, value: str):
        if not value.strip():
            raise ValueError("workspace_id must be a non-empty string")
        return value

    @field_validator("benchmark_id")
    @classmethod
    def validate_benchmark_id(cls, value: str):
        if not value.strip():
            raise ValueError("benchmark_id must be a non-empty string")
        return value
    
    @model_validator(mode="before")
    @classmethod
    def validate_task(cls, data):
        if not data.get("task"):
            raise ValueError("task must be an object")
        return data
    
    def serialize(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)
    
class EvaluationStop(Evaluation):
    
    # Required fields
    workspace_id: Optional[str] = None
    benchmark_id: Optional[str] = None
    task: Optional[TaskCreate] = None
    scenario_id: Optional[List[str]] = None
    strategy_id: Optional[List[str]] = None
    results: Optional[List[Results]] = None
    runtime: Optional[Runtime] = None
    summary: Optional[Dict[str, Any]] = None
    unrated_docs: Optional[List[UnratedDocs]] = None
    took: Optional[StrictInt] = Field(default=None, ge=0)
    
    @model_validator(mode="before")
    @classmethod
    def enrich_meta(cls, input, info):
        meta = input.get("@meta", {})
        if not isinstance(meta, dict):
            raise ValueError("@meta must be an object if provided")
        allowed_keys = { "started_at", "started_by" }
        unexpected_keys = set(meta.keys()) - allowed_keys
        if unexpected_keys:
            raise ValueError(f"@meta only accepts these fields as input: {allowed_keys}")
        meta["stopped_at"] = utils.timestamp()
        input["@meta"] = meta
        return input

    @model_validator(mode="after")
    def validate_meta(self):
        if self.meta.get("stopped_at") and not is_valid_timestamp(self.meta.get("stopped_at")):
            raise ValueError("@meta.stopped_at at must be a valid ISO 8601 timestamp")
        return self
    
    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: List[str]):
        if value is None or not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("scenario_id must be a list of non-empty strings if given")
        return value

    @field_validator("strategy_id")
    @classmethod
    def validate_strategy_id(cls, value: List[str]):
        if value is None or not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("strategy_id must be a list of non-empty strings if given")
        return value
    
    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value):
        if value is None:
            raise ValueError("summary must be an object if given")
        return value
    
    @field_validator("results")
    @classmethod
    def validate_results(cls, value):
        if value is None:
            raise ValueError("results must be an object if given")
        return value
    
    @field_validator("runtime")
    @classmethod
    def validate_runtime(cls, value):
        if value is None:
            raise ValueError("runtime must be an object if given")
        return value
    
    @field_validator("unrated_docs")
    @classmethod
    def validate_unrated_docs(cls, value):
        if value is None:
            raise ValueError("unrated_docs must be a list of objects")
        return value
    
    @field_validator("took", mode="before")
    @classmethod
    def validate_took(cls, value):
        if value is None or isinstance(value, bool):
            raise ValueError("took must be an integer")
        return value
    
    def serialize(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)

class EvaluationComplete(EvaluationStop):
    
    @model_validator(mode="before")
    @classmethod
    def enrich_meta(cls, input, info):
        input = super().enrich_meta(input, info)
        input["@meta"]["status"] = "completed"
        return input
    
class EvaluationFail(EvaluationStop):
    
    @model_validator(mode="before")
    @classmethod
    def enrich_meta(cls, input, info):
        input = super().enrich_meta(input, info)
        input["@meta"]["status"] = "failed"
        return input
    
class EvaluationSkip(EvaluationStop):
    
    @model_validator(mode="before")
    @classmethod
    def enrich_meta(cls, input, info):
        input = super().enrich_meta(input, info)
        input["@meta"]["status"] = "skipped"
        return input