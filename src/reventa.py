"""Modelo secundario: probabilidad de reventa a 3 años (clasificación binaria).

Responsable: Julián. Se toma del notebook 02 (sección 6.2). Contrato usado por MLflow (experimentos/train_reventa.py).

Modelo: HistGradientBoostingClassifier con zona y tipo de predio como variables categóricas. Validación temporal:
entrena con compras de 2015-2017 y evalúa con compras de 2018-2020 (src/datos.division_temporal_reventa). Línea base:
tasa de reventa por zona del entrenamiento. Métricas: auc (mayor es mejor) y brier (menor es mejor).

Uso típico:
    from src import datos, reventa
    df = datos.a_pesos_constantes(datos.cargar_compraventas(), datos.cargar_ipc())
    train, test = datos.division_temporal_reventa(datos.dataset_reventa(df))
    modelo = reventa.entrenar(train, {"max_iter": 200, "learning_rate": 0.05})
    reventa.evaluar(modelo, test)
    reventa.predecir(modelo, "Norte", "2026-09-15", "URBANO", 1)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score

FEATURES = ["zona_cod", "mes_anio", "tipo_cod", "n_previas"]
ORDEN_ZONAS = ["Norte", "Centro", "Sur"]                 # zona_cod 0, 1, 2 (src/datos.py)
TIPOS = ["RURAL", "SIN INFORMACION", "URBANO"]           # tipo_cod 0, 1, 2 (categorías ordenadas de tipo_predio_zona)
CATEGORICAS = ("zona_cod", "tipo_cod")
SEMILLA = 42
RAIZ = Path(__file__).resolve().parent.parent
DIR_MODELOS = Path("models/reventa")                     # relativo a la raíz del repositorio


def _matriz(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Variables de entrada. `mes_anio` y `log_valor_prev` se calculan si se piden y no vienen en el dataset."""
    X = df.copy()
    if "mes_anio" in features and "mes_anio" not in X.columns:
        X["mes_anio"] = X["fecha"].dt.month
    if "log_valor_prev" in features and "log_valor_prev" not in X.columns and "valor_real_prev" in X.columns:
        X["log_valor_prev"] = np.log(X["valor_real_prev"])
    faltan = [c for c in features if c not in X.columns]
    if faltan:
        raise ValueError(f"Faltan las variables {faltan} en el dataset (ver src/datos.dataset_reventa).")
    return X[features].astype(float)


def _features_de(modelo) -> list[str]:
    return list(modelo.feature_names_in_)


def entrenar(train: pd.DataFrame, params: dict | None = None, features: list[str] | None = None):
    """Entrena el clasificador y lo devuelve. `params`: max_iter, learning_rate, max_depth, etc."""
    features = list(features or FEATURES)
    params = {k: v for k, v in (params or {}).items() if v is not None}
    params.setdefault("random_state", SEMILLA)
    cat = [i for i, c in enumerate(features) if c in CATEGORICAS] or None
    modelo = HistGradientBoostingClassifier(categorical_features=cat, **params)
    return modelo.fit(_matriz(train, features), train["y"])


def evaluar(modelo, test: pd.DataFrame, features: list[str] | None = None) -> dict:
    """Diccionario plano de métricas numéricas: auc, brier."""
    features = list(features or _features_de(modelo))
    p = modelo.predict_proba(_matriz(test, features))[:, 1]
    return {"auc": float(roc_auc_score(test["y"], p)), "brier": float(brier_score_loss(test["y"], p))}


def evaluar_linea_base(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Mismas métricas para la línea base (tasa de reventa por zona del entrenamiento)."""
    p = test["zona"].map(train.groupby("zona")["y"].mean()).values
    return {"auc": float(roc_auc_score(test["y"], p)), "brier": float(brier_score_loss(test["y"], p))}


def predecir(modelo, zona: str, fecha: str, tipo_predio: str, n_previas: int) -> float:
    """Probabilidad de reventa a 3 años (0 a 1).

    `tipo_predio`: "URBANO", "RURAL" o "SIN INFORMACION". Las variables de historial que no se conocen quedan vacías (NaN).
    """
    if zona not in ORDEN_ZONAS:
        raise ValueError(f"Zona '{zona}' no válida; use una de {ORDEN_ZONAS}.")
    tipo = str(tipo_predio).strip().upper()
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de predio '{tipo_predio}' no válido; use uno de {TIPOS}.")
    fila = {"zona_cod": ORDEN_ZONAS.index(zona), "mes_anio": pd.Timestamp(fecha).month,
            "tipo_cod": TIPOS.index(tipo), "n_previas": int(n_previas), "n_ventas_previas": int(n_previas)}
    features = _features_de(modelo)
    X = pd.DataFrame([{c: fila.get(c, np.nan) for c in features}], columns=features).astype(float)
    return float(modelo.predict_proba(X)[0, 1])


def guardar(modelo, version: str, metadatos: dict) -> Path:
    """Guarda en models/reventa/<version>/ : modelo.joblib y metadata.json."""
    ruta = RAIZ / DIR_MODELOS / version
    ruta.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, ruta / "modelo.joblib")
    meta = {"modelo": "reventa", "version": version, "fecha": datetime.now().isoformat(timespec="seconds"),
            "algoritmo": "HistGradientBoostingClassifier", "features": _features_de(modelo),
            "objetivo": "1 si el predio se revende en 3 años o menos", "tipos_predio": TIPOS,
            "ventanas": {"entrenamiento": "compras 2015-2017", "prueba": "compras 2018-2020"}, **(metadatos or {})}
    (ruta / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return ruta


def cargar(version: str = "v1"):
    ruta = RAIZ / DIR_MODELOS / version
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Entrene con experimentos/train_reventa.py --guardar-version {version}.")
    return joblib.load(ruta / "modelo.joblib")
