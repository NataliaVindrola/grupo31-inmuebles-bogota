"""Modelo secundario: probabilidad de reventa a 3 años (clasificación binaria).

Responsable: Julián. Se toma del notebook 02 (sección 6.2). Contrato usado por MLflow (experimentos/train_reventa.py).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

FEATURES = ["zona_cod", "mes_anio", "tipo_cod", "n_previas"]
DIR_MODELOS = Path("models/reventa")


def entrenar(train: pd.DataFrame, params: dict | None = None, features: list[str] | None = None):
    """Entrena el clasificador y lo devuelve. `params`: max_iter, learning_rate, max_depth, etc."""
    raise NotImplementedError


def evaluar(modelo, test: pd.DataFrame, features: list[str] | None = None) -> dict:
    """Diccionario plano de métricas numéricas: auc, brier."""
    raise NotImplementedError


def evaluar_linea_base(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Mismas métricas para la línea base (tasa de reventa por zona del entrenamiento)."""
    raise NotImplementedError


def predecir(modelo, zona: str, fecha: str, tipo_predio: str, n_previas: int) -> float:
    """Probabilidad de reventa a 3 años (0 a 1)."""
    raise NotImplementedError


def guardar(modelo, version: str, metadatos: dict) -> Path:
    """Guarda en models/reventa/<version>/ : modelo.joblib y metadata.json."""
    raise NotImplementedError


def cargar(version: str = "v1"):
    raise NotImplementedError
