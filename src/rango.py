"""Modelo principal: rango esperado (p10, p50, p90) del valor registrado, en millones de pesos constantes.

Responsable: Julián. Se toma del notebook 02 (sección 6.1). Este archivo es el CONTRATO que usan MLflow
(experimentos/train_rango.py) y el tablero (dashboard/servicios.py); si cambia una firma, avisar al equipo.

Modelo: un HistGradientBoostingRegressor con pérdida de cuantiles por cada cuantil (0,10, 0,50 y 0,90), sobre
y = log(valor_real). Las predicciones se ordenan para que p10 <= p50 <= p90 (los cuantiles se ajustan por separado
y podrían cruzarse). Las métricas y la línea base son las mismas de experimentos/algoritmos_rango.py (Jorge) y
experimentos/modelos_natalia.py (Natalia), para que todas las corridas se comparen en una sola tabla.

Uso típico:
    from src import datos, rango
    df = datos.a_pesos_constantes(datos.cargar_compraventas(), datos.cargar_ipc())
    train, test = datos.division_temporal_rango(datos.dataset_rango(df))
    modelos = rango.entrenar(train, {"max_iter": 200, "learning_rate": 0.05})
    rango.evaluar(modelos, test)
    rango.guardar(modelos, "v1", {"metricas": ...})
    rango.predecir(rango.cargar("v1"), "Norte", "2026-09-15")
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_pinball_loss

CUANTILES = (0.10, 0.50, 0.90)
FEATURES = ["zona_cod", "t", "mes_anio"]      # variables del modelo; las variantes se prueban desde los parámetros
ORDEN_ZONAS = ["Norte", "Centro", "Sur"]      # mismo orden que src/datos.py (zona_cod 0, 1, 2)
SEMILLA = 42
RAIZ = Path(__file__).resolve().parent.parent
DIR_MODELOS = Path("models/rango")            # relativo a la raíz del repositorio


# ----------------------------------------------------------------------------------------------- utilidades
def _matriz(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Variables de entrada. Calcula `log_valor_prev` si se pide y no viene (a partir de `valor_real_prev`)."""
    X = df.copy()
    if "log_valor_prev" in features and "log_valor_prev" not in X.columns and "valor_real_prev" in X.columns:
        X["log_valor_prev"] = np.log(X["valor_real_prev"])
    faltan = [c for c in features if c not in X.columns]
    if faltan:
        raise ValueError(f"Faltan las variables {faltan} en el dataset (ver src/datos.dataset_rango).")
    return X[features].astype(float)


def _predecir_log(modelos: dict, X: pd.DataFrame) -> dict:
    """Predicciones en escala log, ordenadas para que p10 <= p50 <= p90."""
    pred = np.column_stack([modelos[q].predict(X) for q in CUANTILES])
    pred = np.sort(pred, axis=1)
    return {q: pred[:, i] for i, q in enumerate(CUANTILES)}


def _metricas(y: np.ndarray, pred: dict) -> dict:
    """cobertura_p10_p90, ancho_mediano_musd y pinball por cuantil (y y pred en escala log)."""
    return {"cobertura_p10_p90": float(np.mean((y >= pred[0.10]) & (y <= pred[0.90]))),
            "ancho_mediano_musd": float(np.median(np.exp(pred[0.90]) - np.exp(pred[0.10])) / 1e6),
            **{f"pinball_q{int(round(q * 100))}": float(mean_pinball_loss(y, pred[q], alpha=q)) for q in CUANTILES}}


def _features_de(modelos: dict) -> list[str]:
    return list(modelos[CUANTILES[0]].feature_names_in_)


# ----------------------------------------------------------------------------------------------- contrato
def entrenar(train: pd.DataFrame, params: dict | None = None, features: list[str] | None = None) -> dict:
    """Entrena un modelo por cuantil. Devuelve {cuantil: modelo}. `params`: max_iter, learning_rate, max_depth, etc."""
    features = list(features or FEATURES)
    params = {k: v for k, v in (params or {}).items() if v is not None}
    params.setdefault("random_state", SEMILLA)
    X = _matriz(train, features)
    cat = [features.index("zona_cod")] if "zona_cod" in features else None
    modelos = {}
    for q in CUANTILES:
        m = HistGradientBoostingRegressor(loss="quantile", quantile=q, categorical_features=cat, **params)
        modelos[q] = m.fit(X, train["y"])
    return modelos


def evaluar(modelos: dict, test: pd.DataFrame, features: list[str] | None = None) -> dict:
    """Devuelve un diccionario plano de métricas (todas numéricas, listas para mlflow.log_metrics):

    cobertura_p10_p90, ancho_mediano_musd, pinball_q10, pinball_q50, pinball_q90.
    """
    features = list(features or _features_de(modelos))
    pred = _predecir_log(modelos, _matriz(test, features))
    return _metricas(test["y"].values, pred)


def evaluar_linea_base(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Mismas métricas que `evaluar`, para la línea base (percentiles por zona del último año de entrenamiento)."""
    ultimo = train["year_radica"].max()
    base = train[train["year_radica"] == ultimo].groupby("zona")["y"].quantile(list(CUANTILES)).unstack()
    pred = {q: test["zona"].map(base[q]).values for q in CUANTILES}
    return _metricas(test["y"].values, pred)


def predecir(modelos: dict, zona: str, fecha: str) -> dict:
    """Rango esperado para una zona y una fecha. Devuelve {"p10": float, "p50": float, "p90": float} en M$ constantes.

    Si el modelo usa variables de historial del predio, se dejan vacías (NaN): HistGradientBoosting las admite.
    """
    if zona not in ORDEN_ZONAS:
        raise ValueError(f"Zona '{zona}' no válida; use una de {ORDEN_ZONAS}.")
    f = pd.Timestamp(fecha)
    fila = {"zona_cod": ORDEN_ZONAS.index(zona), "t": (f.year - 2021) * 12 + f.month - 1, "mes_anio": f.month}
    features = _features_de(modelos)
    X = pd.DataFrame([{c: fila.get(c, np.nan) for c in features}], columns=features).astype(float)
    pred = _predecir_log(modelos, X)
    return {f"p{int(round(q * 100))}": float(np.exp(pred[q][0]) / 1e6) for q in CUANTILES}


def guardar(modelos: dict, version: str, metadatos: dict) -> Path:
    """Guarda en models/rango/<version>/ : q10.joblib, q50.joblib, q90.joblib y metadata.json (features, params, métricas)."""
    ruta = RAIZ / DIR_MODELOS / version
    ruta.mkdir(parents=True, exist_ok=True)
    for q in CUANTILES:
        joblib.dump(modelos[q], ruta / f"q{int(round(q * 100))}.joblib")
    meta = {"modelo": "rango", "version": version, "fecha": datetime.now().isoformat(timespec="seconds"),
            "algoritmo": "HistGradientBoostingRegressor (loss=quantile)", "cuantiles": list(CUANTILES),
            "features": _features_de(modelos), "objetivo": "log(valor_real), pesos constantes",
            "ventanas": {"entrenamiento": "2021-2022", "prueba": "2023"}, **(metadatos or {})}
    (ruta / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return ruta


def cargar(version: str = "v1") -> dict:
    """Carga los modelos guardados con `guardar`."""
    ruta = RAIZ / DIR_MODELOS / version
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Entrene con experimentos/train_rango.py --guardar-version {version}.")
    return {q: joblib.load(ruta / f"q{int(round(q * 100))}.joblib") for q in CUANTILES}
