"""Modelo principal: rango esperado (p10, p50, p90) del valor registrado, en millones de pesos constantes.

Responsable: Julián. Se toma del notebook 02 (sección 6.1). Este archivo es el CONTRATO que usan MLflow
(experimentos/train_rango.py) y el tablero (dashboard/servicios.py); si cambia una firma, avisar al equipo.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CUANTILES = (0.10, 0.50, 0.90)
FEATURES = ["zona_cod", "t", "mes_anio"]      # variables del modelo; las variantes se prueban desde los parámetros
DIR_MODELOS = Path("models/rango")


def entrenar(train: pd.DataFrame, params: dict | None = None, features: list[str] | None = None) -> dict:
    """Entrena un modelo por cuantil. Devuelve {cuantil: modelo}. `params`: max_iter, learning_rate, max_depth, etc."""
    raise NotImplementedError


def evaluar(modelos: dict, test: pd.DataFrame, features: list[str] | None = None) -> dict:
    """Devuelve un diccionario plano de métricas (todas numéricas, listas para mlflow.log_metrics):

    cobertura_p10_p90, ancho_mediano_musd, pinball_q10, pinball_q50, pinball_q90.
    """
    raise NotImplementedError


def evaluar_linea_base(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Mismas métricas que `evaluar`, para la línea base (percentiles por zona del último año de entrenamiento)."""
    raise NotImplementedError


def predecir(modelos: dict, zona: str, fecha: str) -> dict:
    """Rango esperado para una zona y una fecha. Devuelve {"p10": float, "p50": float, "p90": float} en M$ constantes."""
    raise NotImplementedError


def guardar(modelos: dict, version: str, metadatos: dict) -> Path:
    """Guarda en models/rango/<version>/ : q10.joblib, q50.joblib, q90.joblib y metadata.json (features, params, métricas)."""
    raise NotImplementedError


def cargar(version: str = "v1") -> dict:
    """Carga los modelos guardados con `guardar`."""
    raise NotImplementedError
