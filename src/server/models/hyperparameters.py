# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import math
import re
from typing import Any, Dict, List, Literal, Optional, Union

# Third-party packages
from pydantic import (
    BaseModel, Field, field_validator, model_serializer, model_validator,
    StrictBool, StrictInt, StrictStr,
)

HYPERPARAMETER_TYPES = ("number", "string", "boolean")
RE_HYPERPARAMETER_NAME = re.compile(r"^\w+$")
# Characters that would break a string embedded in a JSON template unescaped.
RE_UNSAFE_STRING = re.compile(r'["\\\x00-\x1f]')
VALID_OBJECTIVE_METRICS = ("mrr", "ndcg", "precision", "recall")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_value_type(type_: str, value: Any) -> bool:
    """Return whether a value is valid for a hyperparameter type."""
    if type_ == "number":
        return _is_number(value) and math.isfinite(value)
    if type_ == "string":
        return isinstance(value, str)
    if type_ == "boolean":
        return isinstance(value, bool)
    return False


def value_key(value: Any):
    """A hashable key that treats 1 and 1.0 as the same value, and keeps
    numbers, booleans, and strings apart."""
    if isinstance(value, bool):
        return ("boolean", value)
    if _is_number(value):
        return ("number", float(value))
    return ("string", value)


class _DropNone(BaseModel):
    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        data = handler(self)
        return {k: v for k, v in data.items() if v is not None}


def _check_finite(model, fields):
    for field in fields:
        value = getattr(model, field)
        if value is not None and not math.isfinite(value):
            raise ValueError(f"{field} must be a finite number")


def _check_set_values(values: List[Any], min_length: int):
    for v in values:
        if v is None:
            raise ValueError("values must not contain null")
        if not isinstance(v, (str, int, float, bool)):
            raise ValueError("values must be strings, numbers, or booleans")
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("values must be finite numbers")
        if isinstance(v, str) and RE_UNSAFE_STRING.search(v):
            raise ValueError(
                "string values must not contain quotes, backslashes, or control characters"
            )
    if len({ value_key(v) for v in values }) < min_length:
        raise ValueError(f"values must have at least {min_length} distinct values")
    return values


####  Strategy: valid testable values  #########################################

class RangeValues(_DropNone):
    """A numeric range of valid testable values. Either bound can be omitted
    for an unbounded range, such as a boost with a minimum of 0."""
    model_config = { "extra": "forbid", "strict": True }
    type: Literal["range"]
    min: Optional[Union[StrictInt, float]] = None
    max: Optional[Union[StrictInt, float]] = None

    @model_validator(mode="after")
    def validate_range(self):
        _check_finite(self, ("min", "max"))
        if self.min is not None and self.max is not None and self.min >= self.max:
            raise ValueError("min must be less than max")
        return self


class SetValues(_DropNone):
    """A fixed list of valid testable values."""
    model_config = { "extra": "forbid", "strict": True }
    type: Literal["set"]
    values: List[Any] = Field(min_length=2)

    @field_validator("values")
    @classmethod
    def validate_values(cls, value: List[Any]):
        return _check_set_values(value, 2)


TestableValues = Union[RangeValues, SetValues]


def value_is_testable(type_: str, value: Any, testable: Union[TestableValues, Dict[str, Any], None]) -> bool:
    """Return whether a value is one of the valid testable values."""
    if testable is None:
        return True
    if isinstance(testable, BaseModel):
        testable = testable.model_dump()
    if not check_value_type(type_, value):
        return False
    if testable["type"] == "set":
        return value_key(value) in { value_key(v) for v in testable["values"] }
    if testable.get("min") is not None and value < testable["min"]:
        return False
    if testable.get("max") is not None and value > testable["max"]:
        return False
    return True


def validate_testable_values_for_type(type_: str, testable: TestableValues):
    """Check that valid testable values are compatible with a hyperparameter type."""
    if isinstance(testable, RangeValues):
        if type_ != "number":
            raise ValueError(f"a range is not allowed for type {type_}")
    else:
        for v in testable.values:
            if not check_value_type(type_, v):
                raise ValueError(f"set value {v!r} is not a valid {type_}")


class Hyperparameter(_DropNone):
    """A user-defined strategy parameter referenced in a template as
    {{hp.<name>}}. The promoted value is the value the strategy uses today.
    The valid testable values are the values a benchmark may test.

    Boolean hyperparameters always have the testable values true and false."""
    model_config = { "extra": "forbid", "strict": True }
    name: StrictStr
    type: Literal["number", "string", "boolean"]
    promoted_value: Any
    testable_values: Optional[TestableValues] = Field(default=None, discriminator="type")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        if not RE_HYPERPARAMETER_NAME.match(value):
            raise ValueError("name must contain only letters, digits, and underscores")
        return value

    @model_validator(mode="after")
    def validate_hyperparameter(self):
        if not check_value_type(self.type, self.promoted_value):
            raise ValueError(f"promoted_value {self.promoted_value!r} is not a valid {self.type}")
        if isinstance(self.promoted_value, str) and RE_UNSAFE_STRING.search(self.promoted_value):
            raise ValueError(
                "string values must not contain quotes, backslashes, or control characters"
            )
        if self.type == "boolean":
            both = SetValues(type="set", values=[True, False])
            if self.testable_values is not None and (
                not isinstance(self.testable_values, SetValues)
                or { value_key(v) for v in self.testable_values.values } != { value_key(v) for v in both.values }
            ):
                raise ValueError("a boolean hyperparameter always has the testable values true and false")
            self.testable_values = both
        elif self.testable_values is None:
            raise ValueError("testable_values is required")
        validate_testable_values_for_type(self.type, self.testable_values)
        if not value_is_testable(self.type, self.promoted_value, self.testable_values):
            raise ValueError(
                f"promoted_value {self.promoted_value!r} is not one of the valid testable values"
            )
        return self


def validate_hyperparameters(value: List[Hyperparameter]) -> List[Hyperparameter]:
    names = [h.name for h in value]
    if len(names) != len(set(names)):
        raise ValueError("hyperparameter names must be unique")
    return value


class PromotedFrom(_DropNone):
    """Where a strategy's promoted values came from (promotion of a variant)."""
    model_config = { "extra": "forbid", "strict": True }
    strategy_id: StrictStr
    run_id: StrictStr
    variant_id: StrictStr
    values: Dict[str, Any]
    promoted_at: Optional[StrictStr] = None


####  Benchmark: values to test  ###############################################

class RangeToTest(_DropNone):
    """A finite numeric range to test. Grid search takes a `step` or a `count`
    of points, and falls back to the benchmark's `points_per_range`. Random
    search samples the range continuously, snapped to `step` if given. A `log`
    range spaces and samples values logarithmically."""
    model_config = { "extra": "forbid", "strict": True }
    type: Literal["range"]
    min: Union[StrictInt, float]
    max: Union[StrictInt, float]
    step: Optional[Union[StrictInt, float]] = None
    count: Optional[StrictInt] = Field(default=None, ge=2)
    log: bool = False

    @model_validator(mode="after")
    def validate_range(self):
        _check_finite(self, ("min", "max", "step"))
        if self.min >= self.max:
            raise ValueError("min must be less than max")
        if self.step is not None and self.step <= 0:
            raise ValueError("step must be greater than 0")
        if self.step is not None and self.count is not None:
            raise ValueError("step and count are mutually exclusive")
        if self.log:
            if self.min <= 0:
                raise ValueError("min must be greater than 0 for a log range")
            if self.step is not None:
                raise ValueError("a log range uses count instead of step")
        return self


class SetToTest(_DropNone):
    """A list of values to test, which must be some of the valid testable values."""
    model_config = { "extra": "forbid", "strict": True }
    type: Literal["set"]
    values: List[Any] = Field(min_length=2)

    @field_validator("values")
    @classmethod
    def validate_values(cls, value: List[Any]):
        return _check_set_values(value, 2)


ValuesSpec = Union[RangeToTest, SetToTest]


class ValuesToTest(_DropNone):
    """The values a benchmark tests for a hyperparameter name. Applies to every
    selected strategy that defines the hyperparameter, or only to the strategy
    in `strategy_id`. Without `values`, the strategy's valid testable values
    are tested, which needs finite bounds. With `enabled` false, the
    hyperparameter keeps its promoted value."""
    model_config = { "extra": "forbid", "strict": True }
    name: StrictStr
    strategy_id: Optional[StrictStr] = None
    enabled: StrictBool = True
    values: Optional[ValuesSpec] = Field(default=None, discriminator="type")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        if not RE_HYPERPARAMETER_NAME.match(value):
            raise ValueError("name must contain only letters, digits, and underscores")
        return value


class Objective(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    metric: Literal["mrr", "ndcg", "precision", "recall"] = "ndcg"
    aggregation: Literal["mean", "median"] = "mean"


class LatencyConstraint(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    stat: Literal["mean", "median", "p90"] = "median"
    max_ms: Union[StrictInt, float] = Field(gt=0)


class Holdout(BaseModel):
    model_config = { "extra": "forbid", "strict": True }
    ratio: Union[StrictInt, float] = Field(default=0, ge=0, le=0.9)
    seed: Optional[StrictStr] = None


class Optimization(BaseModel):
    """Hyperparameter optimization settings of a benchmark task."""
    model_config = { "extra": "forbid", "strict": True }
    algorithm: Literal["grid", "random"] = "grid"
    sample_size: StrictInt = Field(default=50, ge=1)
    seed: Optional[StrictStr] = None
    points_per_range: StrictInt = Field(default=5, ge=2)
    values_to_test: List[ValuesToTest] = Field(default_factory=list)
    objective: Objective = Field(default_factory=Objective)
    latency_constraint: Optional[LatencyConstraint] = None
    holdout: Holdout = Field(default_factory=Holdout)
    max_concurrent_searches: Optional[StrictInt] = Field(default=None, ge=1)
    store_hits_top_n: StrictInt = Field(default=3, ge=0)

    @field_validator("values_to_test")
    @classmethod
    def validate_values_to_test(cls, value: List[ValuesToTest]):
        keys = [(v.strategy_id, v.name) for v in value]
        if len(keys) != len(set(keys)):
            raise ValueError("values_to_test must have one entry per hyperparameter name and strategy_id")
        return value
