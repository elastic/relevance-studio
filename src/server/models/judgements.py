# Standard packages
from __future__ import annotations
import re
from typing import Any, Optional

# Third-party packages
from pydantic import Field, model_validator

# App packages
from .asset import AssetModel

RE_ISO_8601_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

class JudgementModel(AssetModel):
    project_id: Optional[str] = None
    scenario_id: Optional[str] = None
    index: Optional[str] = None
    doc_id: Optional[str] = None
    rating: Optional[int] = Field(ge=0)
    
    @model_validator(mode="after")
    def validate_params(self) -> JudgementModel:
        """
        Check for required fields differently in creates and updates.
        The Judgements API doesn't use partial updates, but we'll follow the
        same pattern here as the other models for consistency.
        """
        if not self.project_id:
            raise ValueError("project_id is required")
        if not self.scenario_id:
            raise ValueError("scenario_id is required")
        if not self.index:
            raise ValueError("index is required")
        if not self.doc_id:
            raise ValueError("doc_id is required")
        if self.rating is None:
            raise ValueError("rating is required")
        return self

    @model_validator(mode="before")
    @classmethod
    def validate_rating(cls, data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(data.get("rating"), bool):
            raise ValueError("rating must not be a boolean")
        return data