import math
from datetime import datetime, timezone
from statistics import median

from app.repository import ReadingRepository
from app.schemas import Analysis, Metrics, Reading, ReadingInput


class InvalidPeriod(ValueError):
    """The beginning of a statistics period is later than its end."""


def summarize(values: list[float]) -> Metrics:
    return Metrics(
        min=min(values) if values else None,
        max=max(values) if values else None,
        count=len(values),
        sum=math.fsum(values),
        median=median(values) if values else None,
    )


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
        if start is not None and end is not None and start > end:
            raise InvalidPeriod("start must be less than or equal to end")
        rows = self.repository.get_readings(device_id, start, end)
        return Analysis(
            device_id=device_id,
            start=start.astimezone(timezone.utc) if start else None,
            end=end.astimezone(timezone.utc) if end else None,
            **{axis: summarize([row[axis] for row in rows]) for axis in ("x", "y", "z")},
        )
