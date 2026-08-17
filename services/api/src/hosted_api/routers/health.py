from fastapi import APIRouter
from pydantic import BaseModel

from hosted_api import __version__


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def health_payload() -> HealthResponse:
    return HealthResponse(status="ok", service="hosted-api", version=__version__)


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return health_payload()
