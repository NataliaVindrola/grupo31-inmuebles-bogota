"""Comparación de algoritmos para el modelo de rango del valor (p10, p50, p90), registrada en MLflow.

Responsable: Jorge. Script autónomo: la preparación de datos sigue el notebook 02 (secciones 2 y 5-6.1) y no depende de src/,
que todavía no está implementado; cuando exista, se puede cambiar `cargar_dataset` por src.datos.
Cuatro corridas (2 algoritmos x 2 modos), todas con la misma validación temporal del notebook (entrena 2021-2022, prueba 2023):
    hgb_estandar    HistGradientBoostingRegressor con parámetros por defecto
    hgb_optuna      el mismo, afinado con Optuna
    lgbm_estandar   LightGBM (objetivo de cuantiles) con parámetros por defecto
    lgbm_optuna     el mismo, afinado con Optuna
Optuna no toca 2023: entrena con 2021 y valida con 2022, y el modelo final se reentrena con 2021-2022.
Uso, desde la raíz del repositorio:
    python experimentos/algoritmos_rango.py --autor jorge
    python experimentos/algoritmos_rango.py --autor jorge --corridas hgb_estandar lgbm_estandar     # sin Optuna
    python experimentos/algoritmos_rango.py --autor jorge --trials 30
Variable de entorno: MLFLOW_TRACKING_URI (por defecto http://localhost:8050).
"""
import argparse
import os
import time
import warnings

import lightgbm as lgb
import mlflow
import numpy as np
import optuna
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_pinball_loss

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

ZONAS = {"50N": "Norte", "50C": "Centro", "50S": "Sur"}
ORDEN_ZONAS = ["Norte", "Centro", "Sur"]
VALOR_MIN = 5e6
SEMILLA = 42
CUANTILES = [0.10, 0.50, 0.90]
X_COLS = ["zona_cod", "t", "mes_anio"]
CORRIDAS = ["hgb_estandar", "hgb_optuna", "lgbm_estandar", "lgbm_optuna"]


def cargar_dataset(data_dir: str):
    """Devuelve (train 2021-2022, test 2023) con y = log(valor real), t, mes_anio y zona_cod; y el mes de referencia del IPC."""
    cv = pd.read_csv(os.path.join(data_dir, "compraventas_0125_bogota.csv"), dtype=str,
                     usecols=["orip", "valor", "year_radica", "fecha_radica_texto"])
    cv["valor"] = pd.to_numeric(cv["valor"], errors="coerce")
    cv["year_radica"] = pd.to_numeric(cv["year_radica"], errors="coerce").astype("Int64")
    txt = cv["fecha_radica_texto"].str.strip()
    cv["fecha"] = pd.Series(pd.NaT, index=cv.index, dtype="datetime64[ns]")
    for n_car, fmt in {19: "%Y-%m-%d %H:%M:%S", 10: "%d/%m/%Y", 8: "%d/%m/%y"}.items():
        m = txt.str.len() == n_car
        cv.loc[m, "fecha"] = pd.to_datetime(txt[m], format=fmt, errors="coerce")
    cv["zona"] = cv["orip"].str.strip().map(ZONAS)
    cv = cv.dropna(subset=["fecha", "zona"])

    ipc = pd.read_csv(os.path.join(data_dir, "ipc.csv"), sep=None, engine="python", encoding="utf-8-sig")
    ipc.columns = [c.strip().lower() for c in ipc.columns]
    ipc["fecha"] = pd.to_datetime(ipc["fecha"])
    ipc["indice"] = pd.to_numeric(ipc["indice"].astype(str).str.replace(",", "."), errors="coerce")
    indice = ipc.assign(mes=ipc["fecha"].dt.to_period("M")).set_index("mes")["indice"]
    ipc_ref, mes_ref = indice.dropna().iloc[-1], indice.dropna().index[-1]

    bv = cv[(cv["valor"] > 0) & (cv["valor"] >= VALOR_MIN)].copy()
    bv["ipc"] = bv["fecha"].dt.to_period("M").map(indice)
    bv = bv.dropna(subset=["ipc"])
    bv["valor_real"] = bv["valor"] * ipc_ref / bv["ipc"]

    m = bv[bv["year_radica"] >= 2021].copy()
    m["y"] = np.log(m["valor_real"])
    m["t"] = (m["fecha"].dt.year - 2021) * 12 + m["fecha"].dt.month - 1
    m["mes_anio"] = m["fecha"].dt.month
    m["zona_cod"] = m["zona"].map({z: i for i, z in enumerate(ORDEN_ZONAS)})
    return m[m["year_radica"] <= 2022], m[m["year_radica"] == 2023], str(mes_ref)


def matriz(df: pd.DataFrame, algoritmo: str) -> pd.DataFrame:
    """Variables de entrada; para LightGBM la zona va como categoría con los tres niveles fijos."""
    X = df[X_COLS].copy()
    if algoritmo == "lgbm":
        X["zona_cod"] = pd.Categorical(X["zona_cod"], categories=[0, 1, 2])
    return X


def construir(algoritmo: str, q: float, params: dict):
    if algoritmo == "hgb":
        return HistGradientBoostingRegressor(loss="quantile", quantile=q, categorical_features=[0],
                                             random_state=SEMILLA, **params)
    return lgb.LGBMRegressor(objective="quantile", alpha=q, random_state=SEMILLA, verbose=-1, n_jobs=2, **params)


def entrenar(algoritmo: str, params: dict, train: pd.DataFrame) -> dict:
    X = matriz(train, algoritmo)
    return {q: construir(algoritmo, q, params).fit(X, train["y"]) for q in CUANTILES}


def predecir(algoritmo: str, modelos: dict, df: pd.DataFrame) -> dict:
    X = matriz(df, algoritmo)
    pred = {q: modelos[q].predict(X) for q in CUANTILES}
    # los cuantiles se ajustan por separado y pueden cruzarse; se ordenan para que p10 <= p50 <= p90
    ordenado = np.sort(np.column_stack([pred[q] for q in CUANTILES]), axis=1)
    return {q: ordenado[:, i] for i, q in enumerate(CUANTILES)}


def metricas(y: np.ndarray, pred: dict) -> dict:
    return {"cobertura_p10_p90": float(np.mean((y >= pred[0.10]) & (y <= pred[0.90]))),
            "ancho_mediano_musd": float(np.median(np.exp(pred[0.90]) - np.exp(pred[0.10])) / 1e6),
            **{f"pinball_q{int(q * 100)}": float(mean_pinball_loss(y, pred[q], alpha=q)) for q in CUANTILES}}


def linea_base(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Percentiles por zona del último año de entrenamiento (2022), como en el notebook."""
    base = train[train["year_radica"] == 2022].groupby("zona")["y"].quantile(CUANTILES).unstack()
    return metricas(test["y"].values, {q: test["zona"].map(base[q]).values for q in CUANTILES})


def espacio(algoritmo: str, trial: optuna.Trial) -> dict:
    if algoritmo == "hgb":
        return {"max_iter": trial.suggest_int("max_iter", 50, 400),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "max_leaf_nodes": trial.suggest_int("max_leaf_nodes", 8, 64),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 20, 500, log=True),
                "l2_regularization": trial.suggest_float("l2_regularization", 1e-8, 10.0, log=True)}
    return {"n_estimators": trial.suggest_int("n_estimators", 50, 400),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 8, 64),
            "min_child_samples": trial.suggest_int("min_child_samples", 20, 500, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True)}


def afinar(algoritmo: str, train: pd.DataFrame, n_trials: int) -> dict:
    """Optuna (TPE, semilla fija): entrena con 2021, valida con 2022 y minimiza el pinball medio de los tres cuantiles."""
    ajuste, val = train[train["year_radica"] == 2021], train[train["year_radica"] == 2022]

    def objetivo(trial: optuna.Trial) -> float:
        pred = predecir(algoritmo, entrenar(algoritmo, espacio(algoritmo, trial), ajuste), val)
        valor = float(np.mean([mean_pinball_loss(val["y"].values, pred[q], alpha=q) for q in CUANTILES]))
        mlflow.log_metric("val_pinball_medio", valor, step=trial.number)   # curva de la búsqueda en la corrida
        return valor

    estudio = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEMILLA))
    estudio.optimize(objetivo, n_trials=n_trials)
    mlflow.log_metric("val_pinball_medio_mejor", estudio.best_value)
    return estudio.best_params


def correr(nombre: str, train: pd.DataFrame, test: pd.DataFrame, base: dict, a: argparse.Namespace, mes_ref: str) -> None:
    algoritmo, modo = nombre.split("_")
    with mlflow.start_run(run_name=nombre):
        mlflow.set_tags({"autor": a.autor, "algoritmo": algoritmo, "modo": modo})
        t0 = time.time()
        params = afinar(algoritmo, train, a.trials) if modo == "optuna" else {}
        modelos = entrenar(algoritmo, params, train)
        res = metricas(test["y"].values, predecir(algoritmo, modelos, test))
        mlflow.log_params({"algoritmo": algoritmo, "modo": modo, "features": ",".join(X_COLS), "random_state": SEMILLA,
                           "n_train": len(train), "n_test": len(test), "mes_ref_ipc": mes_ref,
                           "n_trials": a.trials if modo == "optuna" else 0,
                           **({"hp_" + k: v for k, v in params.items()} if params else {"hiperparametros": "por defecto"})})
        mlflow.log_metrics({**res, **{f"base_{k}": v for k, v in base.items()}, "tiempo_s": time.time() - t0})
        print(f"[{nombre}] cobertura {res['cobertura_p10_p90']:.3f} | ancho {res['ancho_mediano_musd']:.0f} M$ | "
              f"pinball q10/q50/q90 {res['pinball_q10']:.3f}/{res['pinball_q50']:.3f}/{res['pinball_q90']:.3f} | {time.time() - t0:.0f} s")


def main() -> None:
    ap = argparse.ArgumentParser(description="Compara HistGradientBoosting y LightGBM (estándar y con Optuna) en MLflow")
    ap.add_argument("--autor", default="jorge")
    ap.add_argument("--experimento", default="rango-valor")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--trials", type=int, default=20, help="intentos de Optuna por algoritmo")
    ap.add_argument("--corridas", nargs="+", choices=CORRIDAS, default=CORRIDAS)
    a = ap.parse_args()

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:8050"))
    mlflow.set_experiment(a.experimento)
    train, test, mes_ref = cargar_dataset(a.data_dir)
    print(f"Entrenamiento (2021-2022): {len(train):,} | prueba (2023): {len(test):,} | pesos constantes de {mes_ref}")
    base = linea_base(train, test)
    print(f"[linea_base] cobertura {base['cobertura_p10_p90']:.3f} | ancho {base['ancho_mediano_musd']:.0f} M$")
    for nombre in a.corridas:
        correr(nombre, train, test, base, a, mes_ref)


if __name__ == "__main__":
    main()
