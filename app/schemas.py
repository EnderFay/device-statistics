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


class UserAnalysis(BaseModel):
    user_id: int
    start: datetime | None
    end: datetime | None
    x: Metrics
    y: Metrics
    z: Metrics


class UserDeviceAnalysis(BaseModel):
    user_id: int
    start: datetime | None
    end: datetime | None
    devices: list[Analysis]


class UserInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class DeviceOwnerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int = Field(strict=True, gt=0)


class Device(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: int | None
