# Estructura del repositorio y reparto de la Entrega 2

Grupo 31 · Entrega 2 (domingo 8 de noviembre). Este documento fija **dónde va cada cosa** y **qué contrato une las piezas**, para que
Natalia, Julián y Jorge trabajen en paralelo sin pisarse.

## 1. Árbol

```
grupo31-inmuebles-bogota/
├── data/                  datos (solo los .dvc en Git; el CSV viene de `dvc pull`)            [Natalia]
├── notebooks/             01 exploración, 02 valorización/liquidez/modelos (ya existen)        [todos]
├── reports/figures/       figuras y cifras de los notebooks (ya existe)
├── mockup/                maqueta del tablero de la Entrega 1 (ya existe)
├── src/                   FUENTES DE LOS MODELOS Y DE LOS DATOS (código reutilizable)
│   ├── construir_ipc.py   reconstruye el IPC (ya existe)                                      [Natalia]
│   ├── datos.py           carga, IPC, pesos constantes, datasets y particiones temporales      [Natalia + Julián]
│   ├── rango.py           modelo de rango p10/p50/p90 del valor (entrenar, evaluar, predecir)  [Julián]
│   ├── reventa.py         modelo de reventa a 3 años                                           [Julián]
│   └── tablas.py          genera las tablas del tablero en dashboard/data/                     [Natalia + Julián]
├── models/                MODELOS ENTRENADOS elegidos (rango/v1, reventa/v1) + README          [Julián]
├── experimentos/          scripts con MLflow (train_rango.py, train_reventa.py) + README       [Jorge]
├── dashboard/             FUENTES DEL TABLERO (Dash)                                           [Jorge]
│   ├── app.py  servicios.py  pages/ (segmentos, liquidez, oferta)  assets/  data/
├── docs/                  este documento, capturas (MLflow, commits) y borradores del reporte  [todos]
├── requirements.txt       dependencias de todo el proyecto
└── README.md
```

**Fuentes de los modelos** = `src/` (+ `experimentos/` para entrenarlos con MLflow). **Modelos entrenados** = `models/`. **Fuentes del tablero** = `dashboard/`.
Los notebooks quedan como exploración y evidencia; lo que se reutiliza se pasa a `src/` (no se copia y pega entre notebooks).

## 2. Flujo de datos

```
data/*.dvc ──dvc pull──▶ CSV ──▶ src/datos.py ──┬──▶ src/rango.py / reventa.py ──▶ models/<modelo>/<version>/
                                                │          ▲
                                                │          └── experimentos/train_*.py  ──▶ MLflow (EC2)
                                                └──▶ src/tablas.py ──▶ dashboard/data/*.csv
dashboard/pages/*.py ──▶ dashboard/servicios.py ──▶ (lee dashboard/data/*.csv) y (llama a src/rango.predecir con models/rango/v1)
```

## 3. Contratos (lo que no se cambia sin avisar)

**Julián, `src/rango.py`** (ya están las firmas con su documentación):
`entrenar(train, params, features) -> {cuantil: modelo}`, `evaluar(modelos, test, features) -> dict plano`,
`evaluar_linea_base(train, test) -> dict plano`, `predecir(modelos, zona, fecha) -> {"p10","p50","p90"}` (M$ constantes),
`guardar(modelos, version, metadatos)`, `cargar(version)`.
Métricas (nombres exactos, las usa MLflow): `cobertura_p10_p90`, `ancho_mediano_musd`, `pinball_q10`, `pinball_q50`, `pinball_q90`.

**Julián, `src/reventa.py`:** mismas funciones para el clasificador; métricas `auc` y `brier`; `predecir(...) -> probabilidad`.

**Natalia, `src/datos.py`:** `cargar_compraventas`, `cargar_ipc`, `a_pesos_constantes`, `dataset_rango`, `dataset_reventa` y las dos
particiones temporales (ya están las ventanas: rango 2021–2022 / 2023; reventa compras 2015–2017 / 2018–2020).
Columnas que deben salir de los datasets: están descritas en cada función.

**Natalia y Julián, `src/tablas.py`** (`python -m src.tablas`) deja en `dashboard/data/` (columnas exactas en el archivo):
`segmentos.csv`, `liquidez.csv`, `liquidez_resumen.csv`, `rango_historico.csv`, `cifras_clave.csv`.

**Jorge:** el tablero solo consume esos CSV y `rango.predecir`. Cuando existan, las pantallas se llenan sin tocar más código.

Mientras una pieza no esté lista, las funciones lanzan `NotImplementedError` y el tablero muestra un aviso en lugar de fallar.

## 4. Reglas de trabajo

- **Ramas:** una rama por tarea (`modelos-rango`, `datos-tablas`, `tablero-dash`) y *pull request* o merge a `main`. Commits pequeños y descriptivos; cada uno con **su propio usuario de Git** (así se ve el aporte de cada uno en el reporte).
- **No se suben** el CSV de datos (va por DVC), `mlruns/`, bases de datos de MLflow ni llaves/credenciales.
- **Modelos entrenados:** en `models/<modelo>/<version>/`; menos de 25 MB por archivo en Git, si pesa más, DVC. No se sobrescribe una versión ya usada.
- **Reproducibilidad:** semilla 42, ventanas temporales fijas, parámetros por línea de comandos.
- **Lenguaje del producto:** "referencia histórica", no avalúo; cada cifra con su n e intervalo; segmentos con n < 100 marcados como no concluyentes.

## 5. MLflow (experimentos)

Dos experimentos: `rango-valor` y `reventa-3a`, registrados desde `experimentos/train_*.py`.
El servidor corre en una EC2 (Ubuntu 24.04) con puerto abierto; los pantallazos del reporte deben mostrar el usuario de AWS y la IP de la máquina, y la **misma IP** en la barra del navegador. La instancia queda **detenida** al terminar (no terminada). Responsable: Jorge.

## 6. Entregables y quién empuja cada uno

| Entregable | Se arma con | Responsable principal |
|---|---|---|
| Modelos desarrollados y evaluación | `src/rango.py`, `src/reventa.py`, `models/`, tabla de métricas | Julián |
| Datos, tablas y repositorio | `src/datos.py`, `src/tablas.py`, DVC | Natalia |
| Experimentos y soporte de MLflow | `experimentos/`, pantallazos en `docs/capturas/` | Jorge |
| Tablero | `dashboard/` | Jorge |
| Reporte (≤ 10 páginas) | consolidado desde `docs/` | Natalia (consolida), todos redactan su parte |
| Reporte de trabajo en equipo (≤ 1 página) | tabla de roles, commits, decisiones | todos aportan su fila |

## 7. Calendario

| Día | Meta |
|---|---|
| Mié 4 | Acordar esta estructura y los contratos; `dvc pull` funcionando para todos. |
| Jue 5 | `src/datos.py` y los modelos con las funciones del contrato; esqueleto del tablero corriendo. |
| Vie 6 | `src/tablas.py` generando los CSV; MLflow en EC2 con corridas; pantallas 1 y 2 con datos reales. |
| Sáb 7 | Pantalla 3 con el modelo; capturas; borradores de cada parte del reporte; commits de todos subidos. |
| Dom 8 | Reporte consolidado a las 18:00; entrega antes de las 23:59; detener la EC2. |
