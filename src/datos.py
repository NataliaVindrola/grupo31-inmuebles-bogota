"""Preparacion de datos compartida por los modelos, las tablas y el tablero.

Responsable: Natalia (con Julian). Se toma del notebook 02 (secciones 2 y 3) y no se duplica en otros archivos.
Entrada: data/compraventas_0125_bogota.csv y data/ipc.csv (se obtienen con `dvc pull`).

Las reglas de limpieza viven en src/limpieza.py (limpiar_registro) y son las mismas que
usa `python src/limpieza.py` para generar data/compraventas_limpio.csv:
zona por ORIP, fechas en dos formatos, valor valido (>= 5 millones) y duplicados colapsados
(una misma venta registrada varias veces = misma matricula y fecha).

Uso tipico:
    from src import datos
    df = datos.a_pesos_constantes(datos.cargar_compraventas(), datos.cargar_ipc())
    train, test = datos.division_temporal_rango(datos.dataset_rango(df))
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:                                   # python -m src.tablas  /  from src import datos
    from src import limpieza as _L
except ImportError:                    # ejecutado desde dentro de src/
    import limpieza as _L

ORDEN_ZONAS = ["Norte", "Centro", "Sur"]   # ORIP 50N, 50C y 50S
VALOR_MIN = 5_000_000                       # valores por debajo se consideran inválidos
MES_REF = "2026-09"                         # último mes del IPC; define los "pesos constantes"
SEMILLA = 42

# Columnas adicionales (no son del contrato) que calcula con_historial(); todas usan solo el pasado.
EXTRAS_HISTORIAL = ["n_ventas_previas", "dias_desde_ultima", "valor_real_prev",
                    "ventas_zona_mes_ant", "ventas_zona_3m_ant"]


def cargar_compraventas(ruta: str = "data/compraventas_0125_bogota.csv") -> pd.DataFrame:
    """Lee el CSV, unifica los tres formatos de fecha y agrega `zona`, `predio` (ORIP + matrícula) y `valor_valido`.

    - `predio`: la matrícula ya trae el prefijo de la ORIP (p. ej. 50C-1346790), así que identifica el predio.
    - `valor`: tal como viene (numérico); `valor_valido` = valor >= VALOR_MIN.
    - Se excluyen las ORIP distintas de 50N/50C/50S y se colapsan las ventas duplicadas
      (`n_registros_dia` guarda cuántas filas había).
    """
    df = pd.read_csv(ruta, dtype={"pk": str, "matricula": str, "orip": str}, low_memory=False)
    df = _L.limpiar_registro(df, _L.Bitacora(silencioso=True))
    df = df.rename(columns={"predio_id": "predio"})
    return df.sort_values(["predio", "fecha", "pk"], kind="mergesort").reset_index(drop=True)


def cargar_ipc(ruta: str = "data/ipc.csv") -> pd.Series:
    """Índice mensual de precios (base dic-2018 = 100) indexado por periodo mensual."""
    return _L.cargar_ipc(ruta)


def a_pesos_constantes(df: pd.DataFrame, ipc: pd.Series, mes_ref: str = MES_REF) -> pd.DataFrame:
    """Agrega `valor_real` = valor * ipc[mes_ref] / ipc[mes de la venta]."""
    ref = pd.Period(mes_ref, "M")
    if ref not in ipc.index:
        raise ValueError(f"El mes de referencia {mes_ref} no está en el IPC.")
    out = df.copy()
    idx = out["fecha"].dt.to_period("M").map(ipc)
    out["valor_real"] = out["valor"] * ipc[ref] / idx
    return out


def con_historial(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega las variables de historial (EXTRAS_HISTORIAL), calculadas solo con información anterior.

    - n_ventas_previas: ventas anteriores del mismo predio (desde 2015; no se ve lo anterior a esa fecha).
    - dias_desde_ultima: días desde la venta anterior del predio.
    - valor_real_prev: valor (pesos constantes, solo si fue válido) de la venta anterior.
    - ventas_zona_mes_ant / ventas_zona_3m_ant: ventas de la zona en el mes anterior y promedio de los 3 anteriores.
    Requiere `valor_real` (a_pesos_constantes). Devuelve las filas ordenadas por predio y fecha.
    """
    _requerir(df, ["valor_real", "valor_valido", "predio", "zona", "fecha", "pk"])
    d = df.copy()
    d["predio_id"] = d["predio"]
    d["mes"] = d["fecha"].dt.to_period("M")
    d["_vr_orig"] = d["valor_real"]
    d["valor_real"] = d["valor_real"].where(d["valor_valido"])   # el valor previo solo cuenta si fue válido
    d = _L.agregar_historial(d)
    d = _L.agregar_actividad_zona(d)
    d["valor_real"] = d["_vr_orig"]
    return d.drop(columns=["_vr_orig", "predio_id", "mes"])


def dataset_rango(df: pd.DataFrame) -> pd.DataFrame:
    """Dataset del modelo de rango (2021-2023, solo ventas con valor).

    Columnas mínimas: zona, zona_cod, fecha, year_radica, t (meses desde ene-2021), mes_anio, valor_real, y (= log(valor_real)).
    Columnas adicionales (opcionales para los experimentos): EXTRAS_HISTORIAL.
    `mes_anio` es el mes del año (1 a 12), para capturar estacionalidad.
    """
    d = con_historial(df)
    d = d[d["valor_valido"] & d["year_radica"].between(2021, 2023)].copy()
    d["zona_cod"] = d["zona"].map({z: i for i, z in enumerate(ORDEN_ZONAS)}).astype(int)
    d["t"] = (d["fecha"].dt.year - 2021) * 12 + d["fecha"].dt.month - 1
    d["mes_anio"] = d["fecha"].dt.month
    d["y"] = np.log(d["valor_real"])
    cols = ["zona", "zona_cod", "fecha", "year_radica", "t", "mes_anio", "valor_real", "y"] + EXTRAS_HISTORIAL
    return d[cols].sort_values(["fecha", "zona_cod"], kind="mergesort").reset_index(drop=True)


def dataset_reventa(df: pd.DataFrame, horizonte_dias: int = 1096,
                    solo_seguimiento_completo: bool = True) -> pd.DataFrame:
    """Dataset del modelo de reventa (compras 2015-2020 con reventa observada o censura).

    Columnas mínimas: zona, zona_cod, fecha, year_radica, tipo_cod, n_previas, y (1 si se revendió dentro del horizonte).
    Columnas adicionales (opcionales): dias_desde_ultima, valor_real_prev, ventas_zona_mes_ant, ventas_zona_3m_ant.

    Censura: con `solo_seguimiento_completo=True` se descartan las compras cuyo seguimiento termina antes del
    horizonte (la última venta registrada es la fecha de corte); así `y = 0` significa "no se revendió en el horizonte".
    """
    d = con_historial(df)                                   # ordenado por predio y fecha
    d["_proxima"] = d.groupby("predio", sort=False)["fecha"].shift(-1)
    d["_dias_a_reventa"] = (d["_proxima"] - d["fecha"]).dt.days
    fecha_corte = d["fecha"].max()
    d = d[d["year_radica"].between(2015, 2020)].copy()
    if solo_seguimiento_completo:
        d = d[d["fecha"] + pd.Timedelta(days=horizonte_dias) <= fecha_corte]
    d["y"] = (d["_dias_a_reventa"] <= horizonte_dias).astype(int)   # sin reventa (NaN) -> 0
    d["zona_cod"] = d["zona"].map({z: i for i, z in enumerate(ORDEN_ZONAS)}).astype(int)
    tipo = d["tipo_predio_zona"].fillna("NA") if "tipo_predio_zona" in d.columns else pd.Series("NA", index=d.index)
    d["tipo_cod"] = tipo.astype("category").cat.codes
    d["n_previas"] = d["n_ventas_previas"]
    cols = ["zona", "zona_cod", "fecha", "year_radica", "tipo_cod", "n_previas", "y",
            "dias_desde_ultima", "valor_real_prev", "ventas_zona_mes_ant", "ventas_zona_3m_ant"]
    return d[cols].sort_values(["fecha", "zona_cod"], kind="mergesort").reset_index(drop=True)


def division_temporal_rango(ds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(entrenamiento 2021-2022, prueba 2023)."""
    return ds[ds["year_radica"] <= 2022], ds[ds["year_radica"] == 2023]


def division_temporal_reventa(ds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(entrenamiento: compras 2015-2017, prueba: compras 2018-2020)."""
    return ds[ds["year_radica"] <= 2017], ds[(ds["year_radica"] >= 2018) & (ds["year_radica"] <= 2020)]


def _requerir(df: pd.DataFrame, columnas: list[str]) -> None:
    faltan = [c for c in columnas if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas {faltan}. Usa cargar_compraventas() y luego a_pesos_constantes().")
