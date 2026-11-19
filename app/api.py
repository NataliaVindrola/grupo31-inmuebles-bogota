from fastapi import APIRouter

from app import __version__, schemas
from app.config import settings

api_router = APIRouter()
MODEL_VERSION = "v1"

# Ruta para verificar que la API se esté ejecutando correctamente
@api_router.get("/health", response_model=schemas.Health, status_code=200)
def health() -> dict:
    """
    Indica que la API está viva y qué versiones usa.
    """
    health = schemas.Health(
        name=settings.PROJECT_NAME, 
	api_version=__version__, 
	model_version=MODEL_VERSION,
    )

    return health.model_dump()


