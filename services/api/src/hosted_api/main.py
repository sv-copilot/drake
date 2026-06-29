import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hosted_api import __version__
from hosted_api.routers.health import router as health_router
from hosted_api.routers.read import router as read_router
from hosted_api.routers.sync import router as sync_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hosted Operations API",
        version=__version__,
        description="Read-only scaffold for hosted software operations.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.environ.get("HOSTED_WEB_ORIGIN", "http://127.0.0.1:3000")],
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )
    app.include_router(health_router)
    app.include_router(read_router)
    app.include_router(sync_router)
    return app


app = create_app()
