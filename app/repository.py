from datetime import datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.database import Database
from app.errors import DeviceAlreadyOwned, DuplicateUsername, UserNotFound
from app.models import Device, Reading, User


class ReadingRepository:
    def __init__(self, database: Database):
        self.database = database

    def check_connection(self) -> None:
        with self.database.session() as session:
            session.execute(select(Reading.id).limit(1))

    def add(self, device_id: str, timestamp: datetime, x: float, y: float, z: float) -> int:
        with self.database.session() as session:
            session.execute(insert(Device).values(id=device_id).on_conflict_do_nothing(index_elements=[Device.id]))
            reading = Reading(device_id=device_id, timestamp=timestamp, x=x, y=y, z=z)
            session.add(reading)
            session.flush()
            return reading.id

    def get_readings(
        self, device_id: str, start: datetime | None = None, end: datetime | None = None,
    ) -> list[dict[str, float]]:
        query = select(Reading.x, Reading.y, Reading.z).where(Reading.device_id == device_id)
        if start is not None:
            query = query.where(Reading.timestamp >= start)
        if end is not None:
            query = query.where(Reading.timestamp <= end)
        with self.database.session() as session:
            return [dict(row) for row in session.execute(query).mappings()]


class UserRepository:
    def __init__(self, database: Database):
        self.database = database

    def create_user(self, username: str) -> User:
        try:
            with self.database.session() as session:
                user = User(username=username)
                session.add(user)
                session.flush()
                return user
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) == "23505":
                raise DuplicateUsername("Username already exists") from error
            raise

    def get_user(self, user_id: int) -> User:
        with self.database.session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise UserNotFound("User not found")
            return user

    def get_devices(self, user_id: int) -> list[Device]:
        with self.database.session() as session:
            if session.get(User, user_id) is None:
                raise UserNotFound("User not found")
            return list(session.scalars(select(Device).where(Device.user_id == user_id).order_by(Device.id)))

    def assign_device(self, device_id: str, user_id: int) -> Device:
        with self.database.session() as session:
            if session.get(User, user_id) is None:
                raise UserNotFound("User not found")
            session.execute(insert(Device).values(id=device_id).on_conflict_do_nothing(index_elements=[Device.id]))
            device = session.scalars(
                update(Device)
                .where(Device.id == device_id, or_(Device.user_id.is_(None), Device.user_id == user_id))
                .values(user_id=user_id)
                .returning(Device)
            ).one_or_none()
            if device is None:
                raise DeviceAlreadyOwned("Device already belongs to another user")
            return device

    def get_device_readings(
        self, user_id: int, start: datetime | None = None, end: datetime | None = None,
    ) -> dict[str, list[dict[str, float]]]:
        conditions = [Reading.device_id == Device.id]
        if start is not None:
            conditions.append(Reading.timestamp >= start)
        if end is not None:
            conditions.append(Reading.timestamp <= end)
        query = (
            select(Device.id.label("device_id"), Reading.id.label("reading_id"),
                   Reading.x, Reading.y, Reading.z)
            .outerjoin(Reading, and_(*conditions))
            .where(Device.user_id == user_id)
            .order_by(Device.id, Reading.id)
        )
        with self.database.session() as session:
            if session.get(User, user_id) is None:
                raise UserNotFound("User not found")
            result: dict[str, list[dict[str, float]]] = {}
            for row in session.execute(query).mappings():
                readings = result.setdefault(row["device_id"], [])
                if row["reading_id"] is not None:
                    readings.append({axis: row[axis] for axis in ("x", "y", "z")})
            return result
