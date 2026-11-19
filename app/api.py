from fastapi import APIRouter,  HTTPException
from loguru import logger

from app import __version__, schemas
from app.config import settings
from dashboard import servicios


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


# Veredicto de una oferta frente al rango histórico, más el rango que estima el modelo
@api_router.post("/rango", response_model=schemas.RangoRespuesta, status_code=200)
def rango(entrada: schemas.RangoEntrada) -> dict:
    """
	Dice si el precio de una oferta está por debajo, dentro o por encima del rango histórico de su zona."""

    logger.info(f"Consulta de rango: {entrada}")
    historico = servicios.rango_oferta(entrada.zona, entrada.anio, entrada.precio_musd)

    if historico is None:
        raise HTTPException(status_code=404, detail=f"No hay datos históricos para {entrada.zona} en {entrada.anio}.")

    modelo = servicios.rango_modelo(entrada.zona, entrada.anio)
    return {
        "zona": entrada.zona,
        "anio": entrada.anio,
        "precio_musd": entrada.precio_musd,
        "estado": historico["estado"],
        "historico": {k: historico[k] for k in ("p10", "p25", "p50", "p75", "p90", "n", "mes_ref")},
        "modelo": modelo and {k: modelo[k] for k in ("p10", "p50", "p90")},
    }



@api_router.post("/reventa", response_model=schemas.ReventaRespuesta, status_code=200)
def reventa(entrada: schemas.ReventaEntrada) -> dict:
    """Probabilidad de que un predio se revenda en 3 años o menos, según el modelo, y la referencia de su zona."""

    logger.info(f"Consulta de reventa: {entrada}")
    prob = servicios.prob_reventa_modelo(entrada.zona, entrada.tipo_predio, entrada.ventas_previas)
    if prob is None:
        raise HTTPException(status_code=503, detail="El modelo de reventa no está disponible.")
    resumen = servicios.tabla("liquidez_resumen")
    prob_zona = None
    if resumen is not None:
        fila = resumen[resumen["zona"] == entrada.zona]
        if not fila.empty:
            prob_zona = float(fila.iloc[0]["prob_3a"])
    return {
        "zona": entrada.zona,
        "tipo_predio": entrada.tipo_predio,
        "ventas_previas": entrada.ventas_previas,
        "prob_reventa_3a": prob,
        "prob_zona_3a": prob_zona,
    }
