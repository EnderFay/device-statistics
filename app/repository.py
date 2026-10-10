from datetime import datetime

from app.database import Database


class ReadingRepository:
    def __init__(self, database: Database):
        self.database = database

    def check_connection(self) -> None:
        with self.database.connect() as db:
            db.execute("SELECT 1 FROM app_data LIMIT 1")

    def add(self, device_id: str, timestamp: datetime, x: float, y: float, z: float) -> int:
        with self.database.connect() as db:
            cursor = db.execute(
                "INSERT INTO app_data(device_id, timestamp, x, y, z) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (device_id, timestamp, x, y, z),
            )
            return cursor.fetchone()["id"]

    def get_readings(
        self, device_id: str, start: datetime | None = None, end: datetime | None = None,
    ) -> list[dict[str, float]]:
        query = "SELECT x, y, z FROM app_data WHERE device_id = %s"
        parameters = [device_id]
        if start is not None:
            query += " AND timestamp >= %s"
            parameters.append(start)
        if end is not None:
            query += " AND timestamp <= %s"
            parameters.append(end)
        with self.database.connect() as db:
            return db.execute(query, parameters).fetchall()
