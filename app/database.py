from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


class Database:
    def __init__(self, url: str | None):
        self.url = url

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        if not self.url:
            raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection URL")
        with psycopg.connect(self.url, connect_timeout=10, row_factory=dict_row) as connection:
            yield connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS app_data (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    x DOUBLE PRECISION NOT NULL,
                    y DOUBLE PRECISION NOT NULL,
                    z DOUBLE PRECISION NOT NULL
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS ix_app_data_device_time
                ON app_data(device_id, timestamp)
            """)
