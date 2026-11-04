"""Único punto por el que el tablero obtiene datos y predicciones.

Hoy lee los archivos de dashboard/data/ y llama a src/rango.py; cuando exista la API, solo cambian las funciones de este archivo
(las pantallas no se tocan).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATOS = Path(__file__).parent / "data"


def tabla(nombre: str) -> pd.DataFrame | None:
    """Lee dashboard/data/<nombre>.csv; devuelve None si todavía no se ha generado (las pantallas lo avisan)."""
    ruta = DATOS / f"{nombre}.csv"
    return pd.read_csv(ruta) if ruta.exists() else None


def rango_oferta(zona: str, anio: int, precio_musd: float) -> dict | None:
    """Rango esperado y posición de una oferta (pantalla 3).

    Devuelve {"p10", "p50", "p90", "estado"} con estado en {"por debajo del rango", "dentro del rango", "por encima del rango"},
    o None si el modelo todavía no está disponible.
    """
    try:
        from src import rango

        r = rango.predecir(rango.cargar("v1"), zona, f"{anio}-06-15")
    except (NotImplementedError, FileNotFoundError, ImportError):
        return None
    estado = "por debajo del rango" if precio_musd < r["p10"] else ("por encima del rango" if precio_musd > r["p90"] else "dentro del rango")
    return {**r, "estado": estado}
