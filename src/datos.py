"""Preparación de datos compartida por los modelos, las tablas y el tablero.

Responsable: Natalia (con Julián). Se toma del notebook 02 (secciones 2 y 3) y no se duplica en otros archivos.
Entrada: data/compraventas_0125_bogota.csv y data/ipc.csv (se obtienen con `dvc pull`).
"""
from __future__ import annotations

import pandas as pd

ORDEN_ZONAS = ["Norte", "Centro", "Sur"]   # ORIP 50N, 50C y 50S
VALOR_MIN = 5_000_000                       # valores por debajo se consideran inválidos
MES_REF = "2026-09"                         # último mes del IPC; define los "pesos constantes"
SEMILLA = 42


def cargar_compraventas(ruta: str = "data/compraventas_0125_bogota.csv") -> pd.DataFrame:
    """Lee el CSV, unifica los tres formatos de fecha y agrega `zona`, `predio` (ORIP + matrícula) y `valor_valido`."""
    raise NotImplementedError


def cargar_ipc(ruta: str = "data/ipc.csv") -> pd.Series:
    """Índice mensual de precios (base dic-2018 = 100) indexado por periodo mensual."""
    raise NotImplementedError


def a_pesos_constantes(df: pd.DataFrame, ipc: pd.Series, mes_ref: str = MES_REF) -> pd.DataFrame:
    """Agrega `valor_real` = valor * ipc[mes_ref] / ipc[mes de la venta]."""
    raise NotImplementedError


def dataset_rango(df: pd.DataFrame) -> pd.DataFrame:
    """Dataset del modelo de rango (2021-2023, solo ventas con valor).

    Columnas mínimas: zona, zona_cod, fecha, year_radica, t (meses desde ene-2021), mes_anio, valor_real, y (= log(valor_real)).
    """
    raise NotImplementedError


def dataset_reventa(df: pd.DataFrame, horizonte_dias: int = 1096) -> pd.DataFrame:
    """Dataset del modelo de reventa (compras 2015-2020 con reventa observada o censura).

    Columnas mínimas: zona, zona_cod, fecha, year_radica, tipo_cod, n_previas, y (1 si se revendió dentro del horizonte).
    """
    raise NotImplementedError


def division_temporal_rango(ds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(entrenamiento 2021-2022, prueba 2023)."""
    return ds[ds["year_radica"] <= 2022], ds[ds["year_radica"] == 2023]


def division_temporal_reventa(ds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(entrenamiento: compras 2015-2017, prueba: compras 2018-2020)."""
    return ds[ds["year_radica"] <= 2017], ds[(ds["year_radica"] >= 2018) & (ds["year_radica"] <= 2020)]
