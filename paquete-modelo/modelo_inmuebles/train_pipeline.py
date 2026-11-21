"""Entrena los dos modelos del paquete con los hiperparámetros de config.yml y los guarda en modelo_inmuebles/trained/.

Uso (desde la carpeta paquete-modelo/):
    tox run -e train
    python modelo_inmuebles/train_pipeline.py --compraventas ../data/compraventas_0125_bogota.csv --ipc ../data/ipc.csv

Si la variable de entorno MLFLOW_TRACKING_URI está definida, registra una corrida por modelo en MLflow
(experimentos rango-valor y reventa-3a) con los parámetros, las métricas y las de la línea base.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from modelo_inmuebles import __version__
from modelo_inmuebles.config.core import config
from modelo_inmuebles.modelos import rango, reventa
from modelo_inmuebles.processing import datos


def _registrar_mlflow(experimento: str, nombre: str, params: dict, metricas: dict, base: dict, autor: str) -> None:
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        return
    import mlflow  # solo se necesita si se registra en MLflow

    mlflow.set_experiment(experimento)
    with mlflow.start_run(run_name=nombre):
        mlflow.set_tags({"autor": autor, "origen": "paquete modelo_inmuebles", "version_paquete": __version__})
        mlflow.log_params(params)
        mlflow.log_metrics({**metricas, **{f"base_{k}": v for k, v in base.items()}})
    print(f"   registrado en MLflow: experimento {experimento}, corrida {nombre}")


def entrenar_rango(df, autor: str) -> dict:
    cfg = config["rango"]
    params = {**cfg["hiperparametros"], "random_state": config["semilla"]}
    train, test = datos.division_temporal_rango(datos.dataset_rango(df))
    t0 = time.time()
    modelos = rango.entrenar(train, params, cfg["variables"])
    metricas = rango.evaluar(modelos, test, cfg["variables"])
    base = rango.evaluar_linea_base(train, test)
    rango.guardar(modelos, __version__, {"hiperparametros": params, "origen": cfg["origen"],
                                         "n_train": len(train), "n_test": len(test),
                                         "metricas": metricas, "linea_base": base})
    print(f"[rango]   train {len(train):,} | test {len(test):,} | {time.time() - t0:.0f} s")
    print(f"          modelo {json.dumps({k: round(v, 4) for k, v in metricas.items()})}")
    print(f"          base   {json.dumps({k: round(v, 4) for k, v in base.items()})}")
    _registrar_mlflow(config["mlflow"]["experimento_rango"], f"paquete_rango_v{__version__}",
                      {**params, "features": ",".join(cfg["variables"]), "n_train": len(train), "n_test": len(test)},
                      metricas, base, autor)
    return metricas


def entrenar_reventa(df, autor: str) -> dict:
    cfg = config["reventa"]
    params = {**cfg["hiperparametros"], "random_state": config["semilla"]}
    train, test = datos.division_temporal_reventa(datos.dataset_reventa(df))
    modelo = reventa.entrenar(train, params, cfg["variables"])
    metricas = reventa.evaluar(modelo, test, cfg["variables"])
    base = reventa.evaluar_linea_base(train, test)
    reventa.guardar(modelo, __version__, {"hiperparametros": params, "origen": cfg["origen"],
                                          "n_train": len(train), "n_test": len(test),
                                          "metricas": metricas, "linea_base": base})
    print(f"[reventa] train {len(train):,} | test {len(test):,}")
    print(f"          modelo {json.dumps({k: round(v, 4) for k, v in metricas.items()})}")
    print(f"          base   {json.dumps({k: round(v, 4) for k, v in base.items()})}")
    _registrar_mlflow(config["mlflow"]["experimento_reventa"], f"paquete_reventa_v{__version__}",
                      {**params, "features": ",".join(cfg["variables"]), "n_train": len(train), "n_test": len(test)},
                      metricas, base, autor)
    return metricas


def run_training(compraventas: str, ipc: str, autor: str = "julian") -> None:
    print(f"modelo_inmuebles {__version__}: entrenamiento con {compraventas} e {ipc}")
    df = datos.a_pesos_constantes(datos.cargar_compraventas(compraventas), datos.cargar_ipc(ipc),
                                  config["datos"]["mes_referencia"])
    entrenar_rango(df, autor)
    entrenar_reventa(df, autor)
    print("Modelos guardados en modelo_inmuebles/trained/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Entrena los modelos del paquete modelo_inmuebles")
    ap.add_argument("--compraventas", default=config["datos"]["compraventas"])
    ap.add_argument("--ipc", default=config["datos"]["ipc"])
    ap.add_argument("--autor", default="julian")
    a = ap.parse_args()
    run_training(a.compraventas, a.ipc, a.autor)
