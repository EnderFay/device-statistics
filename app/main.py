import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Database
from app.repository import ReadingRepository, UserRepository
from app.routes import create_router
from app.services import ReadingService, UserService


def create_app(database_url: str | None = None) -> FastAPI:
    database = Database(database_url or os.getenv("DATABASE_URL"))
    repository = ReadingRepository(database)
    service = ReadingService(repository)
    users = UserService(UserRepository(database))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.initialize()
        logging.getLogger("uvicorn.error").info("Swagger UI: http://localhost:8000/docs")
        try:
            yield
        finally:
            database.dispose()

    app = FastAPI(
        title="Device Statistics API",
        description="Collecting device readings and analyzing each x, y, z coordinate.",
        version="1.4.1",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Users"},
            {"name": "Devices"},
            {"name": "Readings"},
            {"name": "Statistics"},
            {"name": "Health"},
        ],
    )
    app.include_router(create_router(service, users))
    return app


app = create_app()
