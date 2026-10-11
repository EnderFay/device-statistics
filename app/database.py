from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import AddConstraint

from app.models import Base, Device, Reading


class Database:
    def __init__(self, url: str | None):
        self.url = url
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            if not self.url:
                raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection URL")
            url = make_url(self.url)
            if url.drivername not in ("postgresql", "postgresql+psycopg"):
                raise ValueError("DATABASE_URL must use PostgreSQL")
            self._engine = create_engine(
                url.set(drivername="postgresql+psycopg"),
                pool_pre_ping=True,
                connect_args={"connect_timeout": 10},
            )
        return self._engine

    @contextmanager
    def session(self) -> Iterator[Session]:
        with Session(self.engine, expire_on_commit=False) as session:
            with session.begin():
                yield session

    def initialize(self) -> None:
        with self.engine.begin() as connection:
            Base.metadata.create_all(connection)
            # Register devices from installations created before users were added.
            connection.execute(
                insert(Device).from_select(["id"], select(Reading.device_id).distinct())
                .on_conflict_do_nothing(index_elements=[Device.id])
            )
            foreign_keys = inspect(connection).get_foreign_keys("app_data")
            if not any(key["constrained_columns"] == ["device_id"] for key in foreign_keys):
                constraint = next(iter(Reading.__table__.foreign_key_constraints))
                connection.execute(AddConstraint(constraint))

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
