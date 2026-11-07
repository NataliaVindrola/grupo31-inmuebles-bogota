"""Corrida de MLflow para el modelo de rango del valor (p10, p50, p90).

Responsable: Jorge. Usa el contrato de src/rango.py y src/datos.py.
Ejemplos:
    python experimentos/train_rango.py --nombre base
    python experimentos/train_rango.py --nombre mas_arboles --max-iter 400 --learning-rate 0.03
    python experimentos/train_rango.py --nombre con_contexto --features zona_cod t mes_anio n_previas
Variables de entorno: MLFLOW_TRACKING_URI (por defecto http://localhost:8050).
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # raíz del repositorio, para `from src import ...`

import mlflow

from src import datos, rango


def leer_argumentos() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Entrena y registra el modelo de rango en MLflow")
    ap.add_argument("--nombre", default="corrida", help="nombre de la corrida en MLflow")
    ap.add_argument("--experimento", default="rango-valor")
    ap.add_argument("--autor", default="sin_autor", help="quién registra la corrida (jorge, julian, natalia); queda como etiqueta")
    ap.add_argument("--max-iter", type=int, default=200)
    ap.add_argument("--learning-rate", type=float, default=0.05)
    ap.add_argument("--max-depth", type=int, default=None)
    ap.add_argument("--features", nargs="+", default=rango.FEATURES)
    ap.add_argument("--guardar-version", default=None, help="si se indica (ej. v1), guarda el modelo en models/rango/<version>/")
    return ap.parse_args()


def main() -> None:
    a = leer_argumentos()
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:8050"))
    mlflow.set_experiment(a.experimento)

    df = datos.a_pesos_constantes(datos.cargar_compraventas(), datos.cargar_ipc())
    train, test = datos.division_temporal_rango(datos.dataset_rango(df))
    params = {"max_iter": a.max_iter, "learning_rate": a.learning_rate, "max_depth": a.max_depth, "random_state": datos.SEMILLA}

    with mlflow.start_run(run_name=a.nombre):
        mlflow.set_tag("autor", a.autor)
        mlflow.log_params({**params, "features": ",".join(a.features), "n_train": len(train), "n_test": len(test)})
        modelos = rango.entrenar(train, params, a.features)
        metricas = rango.evaluar(modelos, test, a.features)
        mlflow.log_metrics(metricas)
        mlflow.log_metrics({f"base_{k}": v for k, v in rango.evaluar_linea_base(train, test).items()})
        if a.guardar_version:
            ruta = rango.guardar(modelos, a.guardar_version, {"params": params, "features": a.features, "metricas": metricas})
            mlflow.log_artifacts(str(ruta), artifact_path="modelo")
        print(f"[{a.nombre}] {metricas}")


if __name__ == "__main__":
    main()
