# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import List, Optional

# Third-party packages
from pydantic import BaseModel, computed_field, Field, field_validator, model_validator

# App packages
from .asset import AssetCreate, AssetUpdate
from .hyperparameters import PromotedFrom, Hyperparameter, validate_hyperparameters
from .. import utils

def _check_undefined_refs(source: str, hyperparameters: List[Hyperparameter]):
    """Every {{hp.*}} reference in a template must have a definition."""
    defined = { h.name for h in hyperparameters }
    undefined = [n for n in utils.extract_hyperparameter_refs(source or "") if n not in defined]
    if undefined:
        raise ValueError(
            "template references undefined hyperparameters: " + ", ".join(undefined)
        )

class TemplateCreate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    lang: str = "mustache"
    source: str = ""

class TemplateUpdate(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    
    # Optional inputs
    lang: Optional[str] = None
    source: Optional[str] = None

class StrategyCreate(AssetCreate):
    
    # Required inputs
    workspace_id: str
    name: str
    
    # Optional inputs
    tags: List[str] = Field(default_factory=list)
    template: TemplateCreate = Field(default_factory=TemplateCreate)
    hyperparameters: List[Hyperparameter] = Field(default_factory=list)
    promoted_from: Optional[PromotedFrom] = None

    @field_validator("hyperparameters")
    @classmethod
    def validate_hyperparameters(cls, value: List[Hyperparameter]):
        return validate_hyperparameters(value)

    @model_validator(mode="after")
    def validate_hyperparameter_refs(self):
        _check_undefined_refs(self.template.source if self.template else "", self.hyperparameters)
        return self

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, value: str):
        if not value.strip():
            raise ValueError("workspace_id must be a non-empty string")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]):
        if not value.strip():
            raise ValueError("name must be a non-empty string")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value

    @computed_field
    @property
    def params(self) -> Optional[List[str]]:
        return utils.extract_params(self.template.source or "") if self.template else []

    @computed_field
    @property
    def hyperparameter_refs(self) -> Optional[List[str]]:
        return utils.extract_hyperparameter_refs(self.template.source or "") if self.template else []
    
class StrategyUpdate(AssetUpdate):
    
    # Required inputs
    workspace_id: str
    
    # Optional inputs
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    template: Optional[TemplateUpdate] = None
    hyperparameters: Optional[List[Hyperparameter]] = None
    promoted_from: Optional[PromotedFrom] = None

    @field_validator("hyperparameters")
    @classmethod
    def validate_hyperparameters(cls, value: Optional[List[Hyperparameter]]):
        if value is None:
            raise ValueError("hyperparameters must be a list if given")
        return validate_hyperparameters(value)

    @model_validator(mode="after")
    def validate_hyperparameter_refs(self):
        # Only checkable when the update carries both the template and the
        # hyperparameter definitions. Otherwise the run validates them.
        if self.template and self.template.source is not None and self.hyperparameters is not None:
            _check_undefined_refs(self.template.source, self.hyperparameters)
        return self

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
            raise ValueError("name must be a non-empty string if given")
        if not value.strip():
            raise ValueError("name must be a non-empty string if given")
        return value
    
    @field_validator("template", mode="before")
    @classmethod
    def validate_template(cls, value):
        if value is None:
            raise ValueError("template must be an object if given")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]):
        if value is None or not all(isinstance(t, str) and t.strip() for t in value):
            raise ValueError("tags must be a list of non-empty strings if given")
        return value

    @computed_field
    @property
    def params(self) -> Optional[List[str]]:
        return utils.extract_params(self.template.source or "") if self.template and self.template.source else None

    @computed_field
    @property
    def hyperparameter_refs(self) -> Optional[List[str]]:
        return utils.extract_hyperparameter_refs(self.template.source or "") if self.template and self.template.source else None
