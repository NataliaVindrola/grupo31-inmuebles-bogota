"""Predicciones con los modelos empaquetados (los que usa la API).

    from modelo_inmuebles.predict import predecir_rango, predecir_reventa
    predecir_rango("Sur", 2023)                      # {'p10': ..., 'p50': ..., 'p90': ..., 'version': '1.0.0'}
    predecir_reventa("Norte", "URBANO", 1)           # {'probabilidad_3a': ..., 'version': '1.0.0'}
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from modelo_inmuebles import __version__
from modelo_inmuebles.modelos import rango, reventa

ZONAS = rango.ORDEN_ZONAS
TIPOS_PREDIO = reventa.TIPOS


@lru_cache(maxsize=None)
def _modelos_rango():
    return rango.cargar(__version__)


@lru_cache(maxsize=None)
def _modelo_reventa():
    return reventa.cargar(__version__)


def predecir_rango(zona: str, anio: int, mes: int = 6) -> dict:
    """Rango p10, p50 y p90 (millones de pesos constantes) para una zona y un mes; por defecto, junio del año."""
    if zona not in ZONAS:
        raise ValueError(f"Zona '{zona}' no válida; use una de {ZONAS}.")
    if not 1 <= int(mes) <= 12:
        raise ValueError("El mes debe estar entre 1 y 12.")
    pred = rango.predecir(_modelos_rango(), zona, f"{int(anio)}-{int(mes):02d}-15")
    return {**pred, "version": __version__}


def predecir_reventa(zona: str, tipo_predio: str = "URBANO", ventas_previas: int = 0,
                     fecha: str | None = None) -> dict:
    """Probabilidad de que el predio se revenda en 3 años o menos."""
    if int(ventas_previas) < 0:
        raise ValueError("ventas_previas no puede ser negativo.")
    p = reventa.predecir(_modelo_reventa(), zona, fecha or date.today().isoformat(), tipo_predio, int(ventas_previas))
    return {"probabilidad_3a": p, "version": __version__}
