from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import AwareDatetime

from app.errors import DeviceAlreadyOwned, DuplicateUsername, InvalidPeriod, UserNotFound
from app.schemas import Analysis, Device, DeviceOwnerInput, Reading, ReadingInput, User, UserInput
from app.services import ReadingService, UserService


DeviceId = Annotated[str, Path(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]


def create_router(service: ReadingService, users: UserService) -> APIRouter:
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

    @router.post("/users", response_model=User, status_code=201, tags=["Users"])
    def create_user(payload: UserInput):
        try:
            return users.create_user(payload)
        except DuplicateUsername as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.get("/users/{user_id}", response_model=User, tags=["Users"])
    def get_user(user_id: Annotated[int, Path(gt=0)]):
        try:
            return users.get_user(user_id)
        except UserNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @router.get("/users/{user_id}/devices", response_model=list[Device], tags=["Users"])
    def get_devices(user_id: Annotated[int, Path(gt=0)]):
        try:
            return users.get_devices(user_id)
        except UserNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @router.put("/devices/{device_id}/owner", response_model=Device, tags=["Devices"])
    def assign_device(device_id: DeviceId, payload: DeviceOwnerInput):
        try:
            return users.assign_device(device_id, payload.user_id)
        except UserNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except DeviceAlreadyOwned as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    return router
