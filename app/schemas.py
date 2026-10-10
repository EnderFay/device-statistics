from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


Number = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=-1e100, le=1e100)]


class ReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: Number
    y: Number
    z: Number
    timestamp: AwareDatetime | None = None


class Reading(BaseModel):
    id: int
    device_id: str
    timestamp: datetime
    x: float
    y: float
    z: float


class Metrics(BaseModel):
    min: float | None
    max: float | None
    count: int
    sum: float
    median: float | None


class Analysis(BaseModel):
    device_id: str
    start: datetime | None
    end: datetime | None
    x: Metrics
    y: Metrics
    z: Metrics
