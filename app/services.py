import math
from datetime import datetime, timezone
from statistics import median

from app.errors import InvalidPeriod
from app.repository import ReadingRepository, UserRepository
from app.schemas import (
    Analysis, Device, Metrics, Reading, ReadingInput, User, UserAnalysis,
    UserDeviceAnalysis, UserInput,
)


def summarize(values: list[float]) -> Metrics:
    return Metrics(
        min=min(values) if values else None,
        max=max(values) if values else None,
        count=len(values),
        sum=math.fsum(values),
        median=median(values) if values else None,
    )


def validate_period(start: datetime | None, end: datetime | None) -> None:
    if start is not None and end is not None and start > end:
        raise InvalidPeriod("start must be less than or equal to end")


def summarize_readings(rows: list[dict[str, float]]) -> dict[str, Metrics]:
    return {axis: summarize([row[axis] for row in rows]) for axis in ("x", "y", "z")}


class ReadingService:
    def __init__(self, repository: ReadingRepository):
        self.repository = repository

    def check_health(self) -> dict[str, str]:
        self.repository.check_connection()
        return {"status": "ok"}

    def add_reading(self, device_id: str, payload: ReadingInput) -> Reading:
        timestamp = (payload.timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc)
        reading_id = self.repository.add(device_id, timestamp, payload.x, payload.y, payload.z)
        return Reading(
            id=reading_id, device_id=device_id, timestamp=timestamp,
            x=payload.x, y=payload.y, z=payload.z,
        )

    def get_statistics(
        self, device_id: str, start: datetime | None = None, end: datetime | None = None,
    ) -> Analysis:
        validate_period(start, end)
        rows = self.repository.get_readings(device_id, start, end)
        return Analysis(
            device_id=device_id,
            start=start.astimezone(timezone.utc) if start else None,
            end=end.astimezone(timezone.utc) if end else None,
            **summarize_readings(rows),
        )


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def create_user(self, payload: UserInput) -> User:
        return User.model_validate(self.repository.create_user(payload.username))

    def get_user(self, user_id: int) -> User:
        return User.model_validate(self.repository.get_user(user_id))

    def get_devices(self, user_id: int) -> list[Device]:
        return [Device.model_validate(device) for device in self.repository.get_devices(user_id)]

    def assign_device(self, device_id: str, user_id: int) -> Device:
        return Device.model_validate(self.repository.assign_device(device_id, user_id))

    def get_statistics(
        self, user_id: int, start: datetime | None = None, end: datetime | None = None,
    ) -> UserAnalysis:
        validate_period(start, end)
        grouped = self.repository.get_device_readings(user_id, start, end)
        rows = [row for readings in grouped.values() for row in readings]
        return UserAnalysis(
            user_id=user_id,
            start=start.astimezone(timezone.utc) if start else None,
            end=end.astimezone(timezone.utc) if end else None,
            **summarize_readings(rows),
        )

    def get_device_statistics(
        self, user_id: int, start: datetime | None = None, end: datetime | None = None,
    ) -> UserDeviceAnalysis:
        validate_period(start, end)
        grouped = self.repository.get_device_readings(user_id, start, end)
        start_utc = start.astimezone(timezone.utc) if start else None
        end_utc = end.astimezone(timezone.utc) if end else None
        return UserDeviceAnalysis(
            user_id=user_id, start=start_utc, end=end_utc,
            devices=[
                Analysis(device_id=device_id, start=start_utc, end=end_utc,
                         **summarize_readings(rows))
                for device_id, rows in grouped.items()
            ],
        )
