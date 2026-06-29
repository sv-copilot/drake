from fastapi import FastAPI

from hosted_api import __version__
from hosted_api.routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hosted Operations API",
        version=__version__,
        description="Read-only scaffold for hosted software operations.",
    )
    app.include_router(health_router)
    return app


app = create_app()
