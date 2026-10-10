from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import AwareDatetime

from app.schemas import Analysis, Reading, ReadingInput
from app.services import InvalidPeriod, ReadingService


DeviceId = Annotated[str, Path(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]


def create_router(service: ReadingService) -> APIRouter:
    router = APIRouter()

    @router.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        return service.check_health()

    @router.post("/devices/{device_id}/readings", response_model=Reading, status_code=201, tags=["Readings"])
    def add_reading(device_id: DeviceId, payload: ReadingInput):
        return service.add_reading(device_id, payload)

    @router.get("/devices/{device_id}/statistics", response_model=Analysis, tags=["Statistics"])
    def statistics(
        device_id: DeviceId,
        start: Annotated[AwareDatetime | None, Query(description="The beginning of the period inclusive, with the time zone.")] = None,
        end: Annotated[AwareDatetime | None, Query(description="The end of the period inclusive, with the time zone.")] = None,
    ):
        try:
            return service.get_statistics(device_id, start, end)
        except InvalidPeriod as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return router
