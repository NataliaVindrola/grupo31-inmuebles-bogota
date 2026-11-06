# Experimentos con MLflow

Responsable: Jorge. Scripts de entrenamiento con registro en MLflow; usan las funciones de `src/` (no tienen lógica de modelo propia).

| Script | Experimento en MLflow | Métricas que registra |
|---|---|---|
| `algoritmos_rango.py` | `rango-valor` | las de `train_rango.py` más `tiempo_s`; 4 corridas: HistGradientBoosting y LightGBM, estándar y con Optuna (autónomo, no usa `src/`) |
| `train_rango.py` | `rango-valor` | `cobertura_p10_p90`, `ancho_mediano_musd`, `pinball_q10/q50/q90` (y las mismas de la línea base con prefijo `base_`) |
| `train_reventa.py` | `reventa-3a` | `auc`, `brier` (y las de la línea base con prefijo `base_`) |

Acuerdo del equipo: cada integrante hace 2 modelos de prueba en su propia VM; se identifican con `--autor jorge|julian|natalia` (etiqueta `autor` en MLflow). Las de Jorge están en `algoritmos_rango.py`.

Cada corrida registra también los parámetros (`max_iter`, `learning_rate`, `max_depth`, `features`, `random_state`, `n_train`, `n_test`).

## Correr desde la raíz del repositorio

```
export MLFLOW_TRACKING_URI=http://localhost:8050     # servidor de MLflow
python experimentos/train_rango.py --nombre base
python experimentos/train_reventa.py --nombre base
```

El servidor de MLflow corre en una EC2; la guía paso a paso (instancia, servidor, datos, corridas, pantallazos y cierre) está en `GUIA_EC2_MLFLOW.md`.
No se versionan `mlruns/` ni bases de datos de MLflow.
