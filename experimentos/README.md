# Experimentos con MLflow

Responsable: Jorge. Scripts de entrenamiento con registro en MLflow; usan las funciones de `src/` (no tienen lógica de modelo propia).

| Script | Experimento en MLflow | Métricas que registra |
|---|---|---|
| `train_rango.py` | `rango-valor` | `cobertura_p10_p90`, `ancho_mediano_musd`, `pinball_q10/q50/q90` (y las mismas de la línea base con prefijo `base_`) |
| `train_reventa.py` | `reventa-3a` | `auc`, `brier` (y las de la línea base con prefijo `base_`) |

Cada corrida registra también los parámetros (`max_iter`, `learning_rate`, `max_depth`, `features`, `random_state`, `n_train`, `n_test`).

## Correr desde la raíz del repositorio

```
export MLFLOW_TRACKING_URI=http://localhost:8050     # servidor de MLflow
python experimentos/train_rango.py --nombre base
python experimentos/train_reventa.py --nombre base
```

El servidor de MLflow corre en una EC2 (ver `docs/ESTRUCTURA.md`, sección MLflow); la guía paso a paso de la máquina se agrega a esta carpeta cuando esté montada.
No se versionan `mlruns/` ni bases de datos de MLflow.
