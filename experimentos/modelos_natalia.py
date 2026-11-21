"""Dos modelos de prueba de Natalia para el rango del valor (p10, p50, p90), registrados en MLflow.

Responsable: Natalia. Misma validacion temporal que algoritmos_rango.py de Jorge (entrena 2021-2022, prueba 2023),
mismo experimento (rango-valor) y mismos nombres de metricas, para que las corridas se comparen en una sola tabla.
A diferencia del script de Jorge, los datos salen de src/datos.py: IPC oficial del DANE, sin ventas duplicadas
y con las variables de historial (solo informacion anterior a cada venta).

Dos corridas, ambas LightGBM con parametros por defecto (asi la unica diferencia entre ellas son las variables):
    lgbm_dane        zona, tiempo y mes del anio (las mismas variables de Jorge) con los datos nuevos
    lgbm_historial   las anteriores + historial del predio y actividad de la zona

Ademas de las metricas de Jorge, registra las del subgrupo de ventas con una venta anterior con valor
(*_con_prev), que es donde el historial del predio puede ayudar.

Uso, desde la raiz del repositorio (con data/compraventas_0125_bogota.csv y data/ipc.csv):
    python experimentos/modelos_natalia.py --autor natalia
    python experimentos/modelos_natalia.py --autor natalia --corridas lgbm_dane
Variable de entorno: MLFLOW_TRACKING_URI (por defecto http://localhost:8050).
"""
import argparse
import os
import sys
import time
import warnings
from pathlib import Path

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import mean_pinball_loss

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import datos as D  # noqa: E402

warnings.filterwarnings("ignore")

SEMILLA = D.SEMILLA
CUANTILES = [0.10, 0.50, 0.90]
BASE = ["zona_cod", "t", "mes_anio"]
HISTORIAL = BASE + ["n_ventas_previas", "dias_desde_ultima", "log_valor_prev",
                    "ventas_zona_mes_ant", "ventas_zona_3m_ant"]
CORRIDAS = {"lgbm_dane": ("base", BASE), "lgbm_historial": ("historial", HISTORIAL)}


def cargar(data_dir: str):
    """(train 2021-2022, test 2023, mes de referencia del IPC) desde src/datos.py."""
    df = D.cargar_compraventas(os.path.join(data_dir, "compraventas_0125_bogota.csv"))
    df = D.a_pesos_constantes(df, D.cargar_ipc(os.path.join(data_dir, "ipc.csv")))
    ds = D.dataset_rango(df)
    ds["log_valor_prev"] = np.log(ds["valor_real_prev"])
    train, test = D.division_temporal_rango(ds)
    return train, test, D.MES_REF


def matriz(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Variables de entrada; la zona va como categoria con los tres niveles fijos."""
    X = df[cols].copy()
    X["zona_cod"] = pd.Categorical(X["zona_cod"], categories=[0, 1, 2])
    return X


def entrenar(train: pd.DataFrame, cols: list) -> dict:
    X = matriz(train, cols)
    return {q: lgb.LGBMRegressor(objective="quantile", alpha=q, random_state=SEMILLA, verbose=-1, n_jobs=2)
            .fit(X, train["y"]) for q in CUANTILES}


def predecir(modelos: dict, df: pd.DataFrame, cols: list) -> dict:
    X = matriz(df, cols)
    pred = {q: modelos[q].predict(X) for q in CUANTILES}
    ordenado = np.sort(np.column_stack([pred[q] for q in CUANTILES]), axis=1)   # p10 <= p50 <= p90
    return {q: ordenado[:, i] for i, q in enumerate(CUANTILES)}


def metricas(y: np.ndarray, pred: dict) -> dict:
    return {"cobertura_p10_p90": float(np.mean((y >= pred[0.10]) & (y <= pred[0.90]))),
            "ancho_mediano_musd": float(np.median(np.exp(pred[0.90]) - np.exp(pred[0.10])) / 1e6),
            **{f"pinball_q{int(q * 100)}": float(mean_pinball_loss(y, pred[q], alpha=q)) for q in CUANTILES}}


def prediccion_base(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Linea base de Jorge: percentiles por zona de 2022, aplicados a cada venta de 2023."""
    base = train[train["year_radica"] == 2022].groupby("zona")["y"].quantile(CUANTILES).unstack()
    return {q: test["zona"].map(base[q]).values for q in CUANTILES}


def subgrupo(y: np.ndarray, pred: dict, base: dict, mask: np.ndarray) -> dict:
    """Metricas del modelo y de la linea base solo para las ventas con una venta anterior con valor."""
    if mask.sum() == 0:
        return {"n_test_con_prev": 0}
    m = metricas(y[mask], {q: pred[q][mask] for q in CUANTILES})
    b = metricas(y[mask], {q: base[q][mask] for q in CUANTILES})
    return {"n_test_con_prev": int(mask.sum()),
            "cobertura_con_prev": m["cobertura_p10_p90"], "ancho_mediano_musd_con_prev": m["ancho_mediano_musd"],
            "pinball_q50_con_prev": m["pinball_q50"], "base_pinball_q50_con_prev": b["pinball_q50"]}


def correr(nombre: str, train: pd.DataFrame, test: pd.DataFrame, base_pred: dict,
           a: argparse.Namespace, mes_ref: str) -> None:
    variables, cols = CORRIDAS[nombre]
    with mlflow.start_run(run_name=nombre):
        mlflow.set_tags({"autor": a.autor, "algoritmo": "lgbm", "modo": "estandar", "variables": variables})
        t0 = time.time()
        modelos = entrenar(train, cols)
        pred = predecir(modelos, test, cols)
        y = test["y"].values
        res = metricas(y, pred)
        base = metricas(y, base_pred)
        sub = subgrupo(y, pred, base_pred, test["valor_real_prev"].notna().values)
        mlflow.log_params({"algoritmo": "lgbm", "modo": "estandar", "variables": variables,
                           "features": ",".join(cols), "random_state": SEMILLA,
                           "n_train": len(train), "n_test": len(test), "mes_ref_ipc": mes_ref,
                           "hiperparametros": "por defecto", "fuente_datos": "src/datos.py (IPC DANE, sin duplicados)"})
        mlflow.log_metrics({**res, **{f"base_{k}": v for k, v in base.items()}, **sub,
                            "tiempo_s": time.time() - t0})
        extra = (f" | con venta previa (n={sub['n_test_con_prev']}): pinball q50 {sub['pinball_q50_con_prev']:.3f} "
                 f"vs base {sub['base_pinball_q50_con_prev']:.3f}") if sub["n_test_con_prev"] else ""
        print(f"[{nombre}] cobertura {res['cobertura_p10_p90']:.3f} | ancho {res['ancho_mediano_musd']:.0f} M$ | "
              f"pinball q10/q50/q90 {res['pinball_q10']:.3f}/{res['pinball_q50']:.3f}/{res['pinball_q90']:.3f} | "
              f"{time.time() - t0:.0f} s{extra}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Dos modelos de prueba (LightGBM) del rango del valor, en MLflow")
    ap.add_argument("--autor", default="natalia")
    ap.add_argument("--experimento", default="rango-valor")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--corridas", nargs="+", choices=list(CORRIDAS), default=list(CORRIDAS))
    a = ap.parse_args()

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:8050"))
    mlflow.set_experiment(a.experimento)
    train, test, mes_ref = cargar(a.data_dir)
    print(f"Entrenamiento (2021-2022): {len(train):,} | prueba (2023): {len(test):,} | pesos constantes de {mes_ref}")
    print(f"Ventas de prueba con venta anterior con valor: {int(test['valor_real_prev'].notna().sum()):,}")
    base_pred = prediccion_base(train, test)
    base = metricas(test["y"].values, base_pred)
    print(f"[linea_base] cobertura {base['cobertura_p10_p90']:.3f} | ancho {base['ancho_mediano_musd']:.0f} M$")
    for nombre in a.corridas:
        correr(nombre, train, test, base_pred, a, mes_ref)


if __name__ == "__main__":
    main()
