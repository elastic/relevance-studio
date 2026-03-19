# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Any, Dict, List, Literal, Optional

# Third-party packages
from pydantic import BaseModel, Field, field_validator

# App packages
from .asset import AssetCreate, AssetUpdate


class Result(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    type: Literal["success", "error", "data"]
    data: Dict[str, Any]

class Step(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    type: str  # "reasoning", "tool_call", or "tool_result"
    reasoning: Optional[str] = None
    tool_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    tool_call_id: Optional[str] = None
    results: Optional[List[Result]] = None

class ModelUsage(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    inference_id: Optional[str] = None
    llm_calls: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

class RoundInput(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    message: str

class RoundResponse(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    message: str

class Round(BaseModel):
    id: str
    status: Optional[str] = None
    input: RoundInput
    steps: List[Step] = Field(default_factory=list)
    started_at: Optional[str] = None  # ISO 8601
    time_to_first_token: Optional[int] = None
    time_to_last_token: Optional[int] = None
    model_usage: Optional[ModelUsage] = None
    response: RoundResponse
    model_config = { "extra": "forbid", "strict": True }

class ConversationsCreate(AssetCreate):
    # Required inputs
    conversation_id: str
    title: Optional[str] = None

    # Optional inputs
    rounds: List[Round] = Field(default_factory=list)

    @field_validator("conversation_id")
    @classmethod
    def validate_ids(cls, value: str):
        if not value.strip():
            raise ValueError("conversation_id must be a non-empty string")
        return value

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]):
        if value is not None and not value.strip():
            raise ValueError("title must be a non-empty string")
        return value

class ConversationsUpdate(AssetUpdate):
    # Optional inputs
    title: Optional[str] = None
    rounds: Optional[List[Round]] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]):
        if value is not None and not value.strip():
            raise ValueError("title must be a non-empty string")
        return value
