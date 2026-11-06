"""Genera las tablas ya calculadas que lee el tablero (pantallas 1 y 2 y el historico de la pantalla 3).

Responsable: Natalia (con Julian). Se toma de los notebooks 01 y 02. Uso:  python -m src.tablas
Salida en dashboard/data/ (los nombres y columnas son el CONTRATO con el tablero):

segmentos.csv         zona, q, rango_min_musd, rango_max_musd, n, mediana_real, ic_inf, ic_sup, suficiente (n >= 100)
liquidez.csv          zona, anios, prob_reventa, n                  (curva de Kaplan-Meier por zona, anios de 0 a 9)
liquidez_resumen.csv  zona, prob_1a, prob_3a, prob_5a, n
rango_historico.csv   zona, anio, p10, p25, p50, p75, p90, n        (M$ constantes de MES_REF)
cifras_clave.csv      cifra, valor                                   (ya existe en reports/figures/cifras_clave_02.csv)

Unidades: mediana_real, ic_inf, ic_sup y prob_* se guardan en PUNTOS PORCENTUALES (4.5 = 4,5 %) cuando
PORCENTAJE = True (como en la maqueta); con False se guardan como fraccion (0.045). Los valores en M$ son
millones de pesos constantes de MES_REF.

Ademas escribe reports/pares_filtros.csv con el paso a paso de los filtros de las ventas repetidas.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    from src import datos as D
except ImportError:
    import datos as D

SALIDA = Path("dashboard/data")
REPORTES = Path("reports")

PORCENTAJE = True        # True: puntos porcentuales (4.5); False: fraccion (0.045)
MIN_N = 100              # segmentos con menos pares se marcan como no concluyentes
N_BOOT = 2000            # remuestreos del intervalo de confianza
NIVEL_IC = 90            # intervalo del 90 %
DIAS_MIN_PAR = 30        # al menos 30 dias entre ventas
DIAS_MIN_ANUAL = 180     # se anualiza solo si pasaron 180 dias o mas
DIAS_ATIPICO = 365       # valor identico y reventa en <= 365 dias = operacion atipica
RETORNO_MIN, RETORNO_MAX = 0.2, 5.0
DIAS_ANIO = 365.25
PASO_ANIOS = 0.1


def _esc(x):
    return x * 100 if PORCENTAJE else x


# ----------------------------------------------------------- ventas repetidas
def construir_pares(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pares de ventas consecutivas del mismo predio, ambas con valor, y la traza de filtros.

    Devuelve (pares_finales, traza). Cada par final trae: zona, fecha1, fecha2, dias, v1, v2, r1, r2,
    ret_nominal, ret_real (anualizados).
    """
    v = df[df["valor"].notna()].sort_values(["predio", "fecha", "pk"], kind="mergesort")
    g = v.groupby("predio", sort=False)
    p = pd.DataFrame({
        "zona": v["zona"],
        "fecha1": g["fecha"].shift(1), "fecha2": v["fecha"],
        "v1": g["valor"].shift(1), "v2": v["valor"],
        "r1": g["valor_real"].shift(1), "r2": v["valor_real"],
    }).dropna(subset=["fecha1"])
    p["dias"] = (p["fecha2"] - p["fecha1"]).dt.days

    traza = [("Pares totales (ventas consecutivas con valor)", len(p))]
    p = p[p["dias"] >= DIAS_MIN_PAR]
    traza.append((f"Al menos {DIAS_MIN_PAR} dias entre ventas", len(p)))
    p = p[(p["v1"] >= D.VALOR_MIN) & (p["v2"] >= D.VALOR_MIN)]
    traza.append(("Ambos valores >= 5 millones", len(p)))
    razon = p["v2"] / p["v1"]
    p = p[(razon >= RETORNO_MIN) & (razon <= RETORNO_MAX)]
    traza.append((f"Retorno entre {RETORNO_MIN}x y {RETORNO_MAX:g}x", len(p)))
    p = p[p["dias"] >= DIAS_MIN_ANUAL]
    traza.append((f"Al menos {DIAS_MIN_ANUAL} dias (se anualiza)", len(p)))
    atipico = (p["v1"] == p["v2"]) & (p["dias"] <= DIAS_ATIPICO)
    p = p[~atipico].copy()
    traza.append((f"Sin operaciones atipicas (valor identico y <= {DIAS_ATIPICO} dias)", len(p)))

    expo = 365.0 / p["dias"]
    p["ret_nominal"] = (p["v2"] / p["v1"]) ** expo - 1
    p["ret_real"] = (p["r2"] / p["r1"]) ** expo - 1
    traza = pd.DataFrame(traza, columns=["filtro", "pares"])
    traza["pct_del_total"] = (traza["pares"] / traza["pares"].iloc[0]).round(3)
    return p.reset_index(drop=True), traza


def mediana_con_ic(x: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    """Mediana e intervalo (NIVEL_IC %) por bootstrap."""
    n = len(x)
    if n == 0:
        return np.nan, np.nan, np.nan
    idx = rng.integers(0, n, size=(N_BOOT, n))
    meds = np.median(x[idx], axis=1)
    a = (100 - NIVEL_IC) / 2
    return float(np.median(x)), float(np.percentile(meds, a)), float(np.percentile(meds, 100 - a))


def tabla_segmentos(pares: pd.DataFrame) -> pd.DataFrame:
    """Zona x quintil del valor de la primera venta (pesos constantes), con mediana real e intervalo."""
    q, bordes = pd.qcut(pares["r1"], 5, labels=False, retbins=True)
    pares = pares.assign(q=q.astype(int) + 1)
    rng = np.random.default_rng(D.SEMILLA)
    filas = []
    for zona in D.ORDEN_ZONAS:
        for k in range(1, 6):
            x = pares.loc[(pares["zona"] == zona) & (pares["q"] == k), "ret_real"].to_numpy()
            med, lo, hi = mediana_con_ic(x, rng)
            filas.append({
                "zona": zona, "q": k,
                "rango_min_musd": round(bordes[k - 1] / 1e6, 1),
                "rango_max_musd": round(bordes[k] / 1e6, 1),
                "n": len(x),
                "mediana_real": round(_esc(med), 2), "ic_inf": round(_esc(lo), 2), "ic_sup": round(_esc(hi), 2),
                "suficiente": len(x) >= MIN_N,
            })
    return pd.DataFrame(filas)


# ------------------------------------------------------------------- liquidez
def kaplan_meier(duracion: np.ndarray, evento: np.ndarray):
    """Estimador de Kaplan-Meier. Devuelve (tiempos_con_evento, supervivencia en esos tiempos)."""
    d = np.asarray(duracion, dtype=float)
    e = np.asarray(evento, dtype=bool)
    orden = np.sort(d)
    t_ev = np.unique(d[e])
    if len(t_ev) == 0:
        return t_ev, np.array([])
    en_riesgo = len(d) - np.searchsorted(orden, t_ev, side="left")
    eventos = np.bincount(np.searchsorted(t_ev, d[e]), minlength=len(t_ev))
    return t_ev, np.cumprod(1.0 - eventos / en_riesgo)


def supervivencia_en(t_ev: np.ndarray, S: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Valor de la curva de supervivencia (escalon) en los tiempos t."""
    t = np.asarray(t, dtype=float)
    if len(S) == 0:
        return np.ones_like(t)
    idx = np.searchsorted(t_ev, t, side="right") - 1
    return np.where(idx < 0, 1.0, S[np.clip(idx, 0, len(S) - 1)])


def duraciones_reventa(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada compra: dias hasta la siguiente venta del mismo predio (evento) o hasta el corte (censura)."""
    d = df.sort_values(["predio", "fecha", "pk"], kind="mergesort")
    proxima = d.groupby("predio", sort=False)["fecha"].shift(-1)
    corte = d["fecha"].max()
    evento = proxima.notna()
    dias = (proxima - d["fecha"]).dt.days.where(evento, (corte - d["fecha"]).dt.days)
    return pd.DataFrame({"zona": d["zona"], "dias": dias.astype(float), "evento": evento})


def tablas_liquidez(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dur = duraciones_reventa(df)
    anios = np.round(np.arange(0, 9 + 1e-9, PASO_ANIOS), 1)
    curvas, resumen = [], []
    for zona in D.ORDEN_ZONAS:
        z = dur[dur["zona"] == zona]
        t_ev, S = kaplan_meier(z["dias"].to_numpy(), z["evento"].to_numpy())
        prob = 1 - supervivencia_en(t_ev, S, anios * DIAS_ANIO)
        prob = np.where(anios * DIAS_ANIO > z["dias"].max(), np.nan, prob)   # no se extrapola
        curvas.append(pd.DataFrame({"zona": zona, "anios": anios, "prob_reventa": np.round(_esc(prob), 3), "n": len(z)}))
        p135 = 1 - supervivencia_en(t_ev, S, np.array([1, 3, 5]) * DIAS_ANIO)
        resumen.append({"zona": zona, "prob_1a": round(_esc(p135[0]), 2), "prob_3a": round(_esc(p135[1]), 2),
                        "prob_5a": round(_esc(p135[2]), 2), "n": len(z)})
    return pd.concat(curvas, ignore_index=True), pd.DataFrame(resumen)


# ------------------------------------------------------------- rango historico
def tabla_rango_historico(df: pd.DataFrame) -> pd.DataFrame:
    """Percentiles del valor registrado (M$ constantes de MES_REF) por zona y anio."""
    v = df[df["valor_valido"] & df["year_radica"].between(2021, 2023)]
    filas = []
    for zona in D.ORDEN_ZONAS:
        for anio in (2021, 2022, 2023):
            x = v.loc[(v["zona"] == zona) & (v["year_radica"] == anio), "valor_real"].to_numpy() / 1e6
            if len(x) == 0:
                continue
            p = np.percentile(x, [10, 25, 50, 75, 90])
            filas.append({"zona": zona, "anio": anio, "p10": round(p[0], 1), "p25": round(p[1], 1),
                          "p50": round(p[2], 1), "p75": round(p[3], 1), "p90": round(p[4], 1), "n": len(x)})
    return pd.DataFrame(filas)


# --------------------------------------------------------------- cifras clave
def tabla_cifras(df, pares, seg, resumen) -> pd.DataFrame:
    anio2 = pares["fecha2"].dt.year
    c = [
        ("n_compraventas", len(df)),
        ("n_con_valor", int(df["valor_valido"].sum())),
        ("pct_con_valor", round(100 * df["valor_valido"].mean(), 1)),
        ("n_pares_valorizacion", len(pares)),
        ("mediana_nominal_anualizada_pct", round(100 * pares["ret_nominal"].median(), 1)),
        ("mediana_real_anualizada_pct", round(100 * pares["ret_real"].median(), 1)),
        ("pct_pares_retorno_real_negativo", round(100 * (pares["ret_real"] < 0).mean(), 1)),
        ("mediana_real_2022_pct", round(100 * pares.loc[anio2 == 2022, "ret_real"].median(), 1)),
        ("mediana_real_2023_pct", round(100 * pares.loc[anio2 == 2023, "ret_real"].median(), 1)),
        ("segmentos_reportables", int(seg["suficiente"].sum())),
        ("segmentos_total", len(seg)),
        ("ancho_mediano_ic_pp", round(float((seg["ic_sup"] - seg["ic_inf"]).median()) * (1 if PORCENTAJE else 100), 1)),
    ]
    for _, r in resumen.iterrows():
        c.append((f"prob_reventa_3a_{r['zona'].lower()}", r["prob_3a"]))
    # dtype=object para que los conteos se guarden como enteros (268) y no como 268.0
    return pd.DataFrame({"cifra": [k for k, _ in c], "valor": pd.Series([v for _, v in c], dtype=object)})


# ----------------------------------------------------------------------- main
COLUMNAS = {
    "segmentos.csv": ["zona", "q", "rango_min_musd", "rango_max_musd", "n", "mediana_real", "ic_inf", "ic_sup", "suficiente"],
    "liquidez.csv": ["zona", "anios", "prob_reventa", "n"],
    "liquidez_resumen.csv": ["zona", "prob_1a", "prob_3a", "prob_5a", "n"],
    "rango_historico.csv": ["zona", "anio", "p10", "p25", "p50", "p75", "p90", "n"],
    "cifras_clave.csv": ["cifra", "valor"],
}


def generar(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    pares, traza = construir_pares(df)
    seg = tabla_segmentos(pares)
    liq, resumen = tablas_liquidez(df)
    return {
        "segmentos.csv": seg,
        "liquidez.csv": liq,
        "liquidez_resumen.csv": resumen,
        "rango_historico.csv": tabla_rango_historico(df),
        "cifras_clave.csv": tabla_cifras(df, pares, seg, resumen),
        "_traza": traza,
    }


def main() -> None:
    df = D.a_pesos_constantes(D.cargar_compraventas(), D.cargar_ipc())
    tablas = generar(df)
    SALIDA.mkdir(parents=True, exist_ok=True)
    REPORTES.mkdir(parents=True, exist_ok=True)
    traza = tablas.pop("_traza")
    for nombre, tabla in tablas.items():
        assert list(tabla.columns) == COLUMNAS[nombre], f"{nombre}: columnas distintas del contrato"
        tabla.to_csv(SALIDA / nombre, index=False)
        print(f"{SALIDA / nombre}  ({len(tabla)} filas)")
    traza.to_csv(REPORTES / "pares_filtros.csv", index=False)
    print(f"{REPORTES / 'pares_filtros.csv'}  ({len(traza)} filas)")
    print("\nFiltros de ventas repetidas:")
    print(traza.to_string(index=False))
    print("\nCifras clave:")
    print(tablas["cifras_clave.csv"].to_string(index=False))


if __name__ == "__main__":
    main()
