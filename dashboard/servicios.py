"""Único punto por el que el tablero obtiene datos, rangos de precio y predicciones de los modelos.

Lee las tablas de dashboard/data/ (las genera `python -m src.tablas`) y los modelos entrenados de models/ (los guardan
experimentos/train_rango.py y train_reventa.py con --guardar-version v1). Cuando exista la API solo cambian las funciones de este
archivo y las pantallas no se tocan.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # raíz del repositorio, para `from src import ...`

DATOS = Path(__file__).parent / "data"
ZONAS = ["Norte", "Centro", "Sur"]
MES_REF = "2026-09"   # mes de los pesos constantes; debe coincidir con MES_REF de src/datos.py
PORCENTAJE = False  # debe coincidir con PORCENTAJE de src/tablas.py (hoy False: las tablas traen fracciones, 0.045 = 4,5 %)
COLUMNAS_PORCENTAJE = ("mediana_real", "ic_inf", "ic_sup", "prob_reventa", "prob_1a", "prob_3a", "prob_5a")


def tabla(nombre: str) -> pd.DataFrame | None:
    """Lee dashboard/data/<nombre>.csv; devuelve None si todavía no se ha generado (las pantallas lo avisan).

    Las columnas de porcentaje se entregan como fracción (0.045), aunque la tabla las guarde en puntos porcentuales.
    """
    ruta = DATOS / f"{nombre}.csv"
    if not ruta.exists():
        return None
    df = pd.read_csv(ruta)
    if PORCENTAJE:
        for c in COLUMNAS_PORCENTAJE:
            if c in df.columns:
                df[c] = df[c] / 100
    return df


def anios_disponibles() -> list[int]:
    t = tabla("rango_historico")
    return sorted(int(a) for a in t["anio"].unique()) if t is not None else []


def rango_oferta(zona: str, anio: int, precio_musd: float) -> dict | None:
    """Rango esperado y posición de una oferta (pantalla 3), en millones de pesos constantes.

    Usa los percentiles del valor registrado por zona y año, que en la validación temporal (corridas de MLflow) igualan o superan a los
    modelos de cuantiles probados. Devuelve p10, p25, p50, p75, p90, n, el mes de referencia del IPC y el estado de la oferta
    ("por debajo del rango", "dentro del rango" o "por encima del rango"); None si falta la tabla o la combinación zona-año.
    """
    t = tabla("rango_historico")
    if t is None:
        return None
    f = t[(t["zona"] == zona) & (t["anio"] == anio)]
    if f.empty:
        return None
    r = f.iloc[0]
    estado = "por debajo del rango" if precio_musd < r["p10"] else ("por encima del rango" if precio_musd > r["p90"] else "dentro del rango")
    return {**{k: float(r[k]) for k in ("p10", "p25", "p50", "p75", "p90")}, "n": int(r["n"]), "mes_ref": str(r["mes_ref_ipc"]) if "mes_ref_ipc" in r.index else MES_REF, "estado": estado}


# ------------------------------------------------------------------------------------------- modelos (Julián)
VERSION_MODELOS = "v1"
TIPOS_PREDIO = ["URBANO", "RURAL", "SIN INFORMACION"]


@lru_cache(maxsize=None)
def _modelo(nombre: str, version: str = VERSION_MODELOS):
    """Carga una sola vez el modelo de models/<nombre>/<version>/; None si todavía no se ha entrenado."""
    try:
        from src import rango, reventa
        return {"rango": rango, "reventa": reventa}[nombre].cargar(version)
    except (FileNotFoundError, ImportError):
        return None


def rango_modelo(zona: str, anio: int, precio_musd: float | None = None) -> dict | None:
    """Rango p10, p50 y p90 que estima el modelo de rango (models/rango/v1) para la zona, a mitad del año elegido.

    Devuelve también el estado de la oferta frente a ese rango; None si el modelo no está entrenado.
    """
    modelos = _modelo("rango")
    if modelos is None:
        return None
    from src import rango
    r = rango.predecir(modelos, zona, f"{int(anio)}-06-15")
    if precio_musd is not None:
        r["estado"] = ("por debajo del rango" if precio_musd < r["p10"]
                       else ("por encima del rango" if precio_musd > r["p90"] else "dentro del rango"))
    return r


def prob_reventa_modelo(zona: str, tipo_predio: str, n_previas: int, fecha: str | None = None) -> float | None:
    """Probabilidad de reventa a 3 años que estima el modelo de reventa (models/reventa/v1); None si no está entrenado."""
    modelo = _modelo("reventa")
    if modelo is None:
        return None
    from src import reventa
    return reventa.predecir(modelo, zona, fecha or f"{MES_REF}-15", tipo_predio, int(n_previas))
