# Standard packages
import re
from typing import Optional

# Third-party packages
from pydantic import BaseModel, model_validator, ValidationInfo

# App packages
from .. import utils

RE_ISO_8601_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

def valid_timestamp(ts):
    return RE_ISO_8601_TIMESTAMP.match(ts)

class MetaModel(BaseModel):
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_meta_fields(cls, data, info: ValidationInfo):
        """
        Check for required fields differently in creates and updates.
        """
        if not isinstance(data, dict):
            return data
        context = info.context or {}
        is_partial = context.get("is_partial", False)
        created_at = data.get("created_at", None)
        created_by = data.get("created_by", None)
        updated_at = data.get("updated_at", None)
        updated_by = data.get("updated_by", None)
        if not is_partial:
            if not isinstance(created_at, str) or not valid_timestamp(created_at):
                raise ValueError("created_at must be a valid ISO 8601 string")
            if created_by is None:
                raise ValueError("created_by must not be None")
        if is_partial:
            if not isinstance(updated_at, str) or not valid_timestamp(updated_at):
                raise ValueError("updated_at must be a valid ISO 8601 string")
            if updated_by is None:
                raise ValueError("updated_by must not be None")
        return data
    
    @staticmethod
    def apply_meta_create(doc, user: str = "unknown"):
        """
        Static function for applying @meta.created_* fields.
        """
        doc.pop("@meta", None)
        doc["@meta"] = {
            "created_at": utils.timestamp(),
            "created_by": user, # TODO: Implement
            "updated_at": None,
            "updated_by": None,
        }
        return doc
    
    @staticmethod
    def apply_meta_update(doc_partial, user: str = "unknown"):
        """
        Static function for applying @meta.updated_* fields.
        """
        doc_partial.pop("@meta", None)
        doc_partial["@meta"] = {
            "updated_at": utils.timestamp(),
            "updated_by": user, # TODO: Implement
        }
        return doc_partial