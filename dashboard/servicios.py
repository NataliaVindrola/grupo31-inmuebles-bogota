"""Único punto por el que el tablero obtiene datos y rangos de precio.

Hoy lee las tablas de dashboard/data/ (las genera `python -m src.tablas`); cuando exista la API solo cambian las funciones de este
archivo y las pantallas no se tocan.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATOS = Path(__file__).parent / "data"
ZONAS = ["Norte", "Centro", "Sur"]
MES_REF = "2026-09"   # mes de los pesos constantes; debe coincidir con MES_REF de src/datos.py
PORCENTAJE = True   # debe coincidir con PORCENTAJE de src/tablas.py: True = las tablas traen puntos porcentuales (4.5 = 4,5 %)
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
