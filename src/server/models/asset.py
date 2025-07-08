# Standard packages
from __future__ import annotations

# Third-party packages
from pydantic import BaseModel, Field, model_validator, ValidationInfo

# App packages
from .meta import MetaModel
from .. import utils

class AssetModel(BaseModel):
    meta: MetaModel = Field(alias='@meta', default=None)

    @model_validator(mode="before")
    @classmethod
    def apply_meta(cls, data, info: ValidationInfo):
        context = info.context or {}
        user = context.get("user", "unknown")
        is_partial = context.get("is_partial", False)
        if "@meta" not in data:
            data["@meta"] = {}
        if is_partial:
            data["@meta"]["updated_at"] = utils.timestamp()
            data["@meta"]["updated_by"] = user
        else:
            data["@meta"]["created_at"] = utils.timestamp()
            data["@meta"]["created_by"] = user
            data["@meta"]["updated_at"] = None
            data["@meta"]["updated_by"] = None
        return data