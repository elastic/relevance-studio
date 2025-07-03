# Standard packages
from __future__ import annotations
from typing import List, Optional, Any

# Third-party packages
from pydantic import BaseModel, Field

class EvaluationModel(BaseModel):
    meta: MetaModel = Field(alias='@meta')
    project_id: str
    benchmark_id: str
    scenario_id: str
    strategy_id: str
    task: TaskModel
    results: Optional[ResultsModel]
    runtime: Optional[RuntimeModel]
    summary: Any
    unrated_docs: Optional[UnratedDocsModel]
    took: Optional[int]

class MetaModel(BaseModel):
    status: str
    created_at: str
    started_at: Optional[str]
    stopped_at: Optional[str]

class TaskModel(BaseModel):
    metrics: List[str]
    k: int
    strategies: TaskStrategiesModel
    scenarios: TaskScenariosModel

class TaskScenariosModel(BaseModel):
    ids_: List[str] = Field(alias='_ids')
    tags: List[str]
    sample_size: Optional[int]
    sample_seed: Optional[str]

class TaskStrategiesModel(BaseModel):
    ids_: List[str] = Field(alias='_ids')
    tags: List[str]

class ResultsModel(BaseModel):
    strategy_id: str
    searches: List[SearchResultModel]

class SearchResultModel(BaseModel):
    scenario_id: str
    metrics: MetricsModel
    hits: HitsModel

class HitsModel(BaseModel):
    hit: HitModel
    rating: Optional[int]

class MetricsModel(BaseModel):
    dcg: Optional[float]
    err: Optional[float]
    mrr: Optional[float]
    ndcg: Optional[float]
    precision: Optional[float]
    recall: Optional[float]

class HitModel(BaseModel):
    id_: str = Field(alias='_id')
    index_: str = Field(alias='_index')
    score_: Optional[float] = Field(alias='_score')
    ignored_: Optional[str] = Field(alias='_ignored')

class RuntimeModel(BaseModel):
    indices: Any
    scenarios: Any
    strategies: Any
    judgements: Any

class UnratedDocsModel(BaseModel):
    id_: str = Field(alias='_id')
    index_: str = Field(alias='_index')
    count: int
    strategies: str
    scenarios: str