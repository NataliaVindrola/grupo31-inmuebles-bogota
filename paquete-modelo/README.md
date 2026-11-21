# modelo-inmuebles-bogota (paquete `modelo_inmuebles`)

Paquete con los dos modelos supervisados del proyecto del Grupo 31 (MIAD, Despliegue de Soluciones Analíticas):

| Modelo | Qué predice | Algoritmo | Variables |
|---|---|---|---|
| Rango | p10, p50 y p90 del valor registrado de una compraventa, en millones de pesos constantes | HistGradientBoostingRegressor por cuantiles (hiperparámetros de la corrida `hgb_optuna` en MLflow) | zona, tiempo y mes del año |
| Reventa | probabilidad de que el predio se revenda en 3 años o menos | HistGradientBoostingClassifier (corrida `hgb_reventa_base`) | zona, mes, tipo de predio y ventas previas |

Los hiperparámetros, las variables y las rutas de los datos están en `modelo_inmuebles/config.yml`.

## Estructura

```
paquete-modelo/
├── modelo_inmuebles/
│   ├── config.yml            hiperparámetros, variables, rutas de datos y experimentos de MLflow
│   ├── VERSION               versión del paquete (también nombra la carpeta de los modelos entrenados)
│   ├── config/core.py        lectura de config.yml
│   ├── processing/           limpieza y preparación de datos (copia de src/limpieza.py y src/datos.py)
│   ├── modelos/              rango.py y reventa.py: entrenar, evaluar, línea base, predecir, guardar y cargar
│   ├── train_pipeline.py     entrena los dos modelos y los guarda en trained/<modelo>/<versión>/
│   ├── predict.py            predecir_rango() y predecir_reventa(), usadas por la API
│   └── trained/              modelos entrenados (.joblib) y metadata.json con métricas
├── tests/                    pruebas del paquete (pytest)
├── requirements/             dependencias de uso, de pruebas y de entrenamiento
├── tox.ini                   ambientes train, test_package y test
├── setup.py, pyproject.toml, MANIFEST.in
```

## Entrenar y probar (desde `paquete-modelo/`)

Requiere `../data/compraventas_0125_bogota.csv` y `../data/ipc.csv` (índice del DANE), que se obtienen con `dvc pull`.

```
pip install tox
tox run -e train          # entrena los dos modelos
tox run -e test_package   # entrena y corre las pruebas
tox run -e test           # solo las pruebas, con los modelos ya guardados
```

Si se define `MLFLOW_TRACKING_URI` (por ejemplo `http://localhost:8050`), el entrenamiento registra una corrida por modelo
en los experimentos `rango-valor` y `reventa-3a`.

## Construir e instalar el paquete

```
pip install build
python -m build                    # genera dist/modelo_inmuebles_bogota-<versión>-py3-none-any.whl
pip install dist/modelo_inmuebles_bogota-1.0.0-py3-none-any.whl
```

## Usar

```python
from modelo_inmuebles.predict import predecir_rango, predecir_reventa

predecir_rango("Sur", 2023)                        # {'p10': ..., 'p50': ..., 'p90': ..., 'version': '1.0.0'}
predecir_reventa("Norte", "URBANO", ventas_previas=1)   # {'probabilidad_3a': ..., 'version': '1.0.0'}
```
