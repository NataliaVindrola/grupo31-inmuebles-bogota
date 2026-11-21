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

## Corridas de Julián (modelos de `src/rango.py` y `src/reventa.py`)

Usan `train_rango.py` y `train_reventa.py`, es decir, el contrato de `src/` y los datos de `src/datos.py` (IPC del DANE, sin duplicados).

| Corrida | Experimento | Qué cambia | Comando |
|---|---|---|---|
| `hgb_rango_v1` | `rango-valor` | HistGradientBoosting por cuantiles con zona, tiempo y mes del año; se guarda como `models/rango/v1` (lo usa el tablero) | `python experimentos/train_rango.py --autor julian --nombre hgb_rango_v1 --guardar-version v1` |
| `hgb_reventa_base` | `reventa-3a` | clasificador con zona, mes, tipo de predio y ventas previas (notebook 02); se guarda como `models/reventa/v1` | `python experimentos/train_reventa.py --autor julian --nombre hgb_reventa_base --guardar-version v1` |
| `hgb_reventa_historial` | `reventa-3a` | lo anterior + días desde la venta anterior y actividad de la zona (mes anterior y promedio de 3 meses) | `python experimentos/train_reventa.py --autor julian --nombre hgb_reventa_historial --features zona_cod mes_anio tipo_cod n_previas dias_desde_ultima ventas_zona_mes_ant ventas_zona_3m_ant` |

En reventa no se usa el valor de la venta anterior: las compras de entrenamiento (2015-2017) no tienen valor registrado (el registro trae valor solo desde 2021).
