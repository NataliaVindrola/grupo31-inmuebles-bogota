"""
limpieza.py - Limpieza, deflactacion y variables de historial del registro de
compraventas de Bogota (IGAC-SNR, codigo 0125).

Entradas (versionadas con DVC):
    data/compraventas_0125_bogota.csv   registro crudo
    data/ipc.csv                        indice oficial DANE (fecha, indice)

Salida:
    data/compraventas_limpio.csv        una fila por venta, lista para modelar
    reports/limpieza_resumen.csv        filas que entran y salen en cada paso

Uso (desde la raiz del proyecto):
    python src/limpieza.py
    python src/limpieza.py --mes-ref 2026-09

Pasos de limpieza (en orden):
    1. Zona registral: 50N=Norte, 50C=Centro, 50S=Sur; se excluyen otras ORIP.
    2. Fechas: se convierten los dos formatos del registro; se verifica el anio.
    3. Valor: se conserva solo si es >= 5 millones (menores se marcan como vacios).
    4. Duplicados: una misma venta registrada varias veces (mismo predio y fecha)
       se colapsa en una fila; se conserva el mayor valor y se cuenta cuantas
       filas habia en n_registros_dia.
    5. Deflactacion: valor_real = valor * IPC(mes_ref) / IPC(mes de la venta).
    6. Historial del predio y actividad de la zona, calculados SOLO con
       informacion anterior a la fecha de la venta (sin fuga de informacion).

Los pasos 1 a 4 viven en limpiar_registro(), que tambien usa src/datos.py
(cargar_compraventas) para que los modelos, las tablas y este script apliquen
exactamente las mismas reglas.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

ZONAS = {"50N": "Norte", "50C": "Centro", "50S": "Sur"}
VALOR_MINIMO = 5_000_000
RE_CORTA = r"^\d{1,2}/\d{1,2}/\d{2}$"
RE_ISO = r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}:\d{2}(\.\d+)?)?$"


# ---------------------------------------------------------------- utilidades
class Bitacora:
    """Registra cuantas filas hay despues de cada paso (evidencia para la Guia 4)."""

    def __init__(self, silencioso=False):
        self.filas = []
        self.silencioso = silencioso

    def anotar(self, paso, antes, despues, nota=""):
        self.filas.append({"paso": paso, "filas_antes": antes,
                           "filas_despues": despues, "diferencia": despues - antes,
                           "nota": nota})
        if not self.silencioso:
            print(f"{paso:<46} {antes:>9,} -> {despues:>9,}  {nota}")

    def guardar(self, ruta):
        os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
        pd.DataFrame(self.filas).to_csv(ruta, index=False)


def parsear_fechas(serie):
    """Convierte los formatos conocidos del registro: dd/mm/aa y ISO."""
    s = serie.astype(str).str.strip()
    corta = s.str.match(RE_CORTA)
    iso = s.str.match(RE_ISO)
    fecha = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    fecha[corta] = pd.to_datetime(s[corta], format="%d/%m/%y", errors="coerce")
    try:
        fecha[iso] = pd.to_datetime(s[iso], format="ISO8601", errors="coerce")
    except (ValueError, TypeError):  # pandas antiguo
        fecha[iso] = pd.to_datetime(s[iso], errors="coerce")
    return fecha


def cargar_ipc(ruta):
    ipc = pd.read_csv(ruta)
    if not {"fecha", "indice"} <= set(ipc.columns):
        raise ValueError(f"{ruta} debe tener las columnas fecha e indice.")
    ipc["mes"] = pd.to_datetime(ipc["fecha"]).dt.to_period("M")
    return ipc.set_index("mes")["indice"].astype(float)


def indice_mes(periodo):
    """Entero unico por mes (anio*12 + mes), para cruces y desfases."""
    return periodo.dt.year * 12 + periodo.dt.month


# ------------------------------------------------------------------- limpieza
def limpiar_registro(df, bit):
    """Pasos 1 a 4: zona, fechas, valor valido y duplicados. No deflacta.

    Deja `valor` tal como viene (numerico) y agrega `valor_valido` (>= 5 millones).
    """
    n = len(df)
    bit.anotar("0. Registro crudo", n, n)
    df = df.copy()

    # 1. Zona registral
    df["orip"] = df["orip"].astype(str).str.strip().str.upper()
    df["zona"] = df["orip"].map(ZONAS)
    antes = len(df)
    df = df[df["zona"].notna()].copy()
    bit.anotar("1. Excluir ORIP fuera de 50N/50C/50S", antes, len(df))

    # 2. Fechas
    df["fecha"] = parsear_fechas(df["fecha_radica_texto"])
    antes = len(df)
    df = df[df["fecha"].notna()].copy()
    bit.anotar("2. Excluir fechas no convertibles", antes, len(df))
    desfase = (df["fecha"].dt.year != pd.to_numeric(df["year_radica"], errors="coerce")).sum()
    if desfase:
        print(f"   ADVERTENCIA: {desfase:,} filas donde el anio de la fecha no coincide con year_radica")

    # 3. Valor valido (>= 5 millones); la fila se conserva siempre (sirve para liquidez)
    valor = pd.to_numeric(df["valor"], errors="coerce")
    bajos = int(((valor > 0) & (valor < VALOR_MINIMO)).sum() + (valor == 0).sum())
    df["valor"] = valor
    df["valor_valido"] = valor >= VALOR_MINIMO
    bit.anotar("3. Valor < 5 millones o cero = no valido", len(df), len(df),
               f"({bajos:,} valores invalidos; la fila se conserva para liquidez)")

    # 4. Duplicados: misma venta (predio + fecha) registrada varias veces
    df["predio_id"] = df["matricula"].astype(str).str.strip().str.upper()
    df["n_registros_dia"] = df.groupby(["predio_id", "fecha"])["pk"].transform("size")
    antes = len(df)
    df = (df.sort_values(["predio_id", "fecha", "valor"], ascending=[True, True, False],
                         na_position="last", kind="mergesort")
            .drop_duplicates(["predio_id", "fecha"], keep="first")
            .copy())
    bit.anotar("4. Colapsar duplicados (predio + fecha)", antes, len(df))
    return df


def limpiar(df, ipc, mes_ref, bit):
    df = limpiar_registro(df, bit)
    # En el archivo limpio el valor invalido queda vacio
    df["valor"] = df["valor"].where(df["valor_valido"])

    # 5. Deflactacion a pesos del mes de referencia
    df["mes"] = df["fecha"].dt.to_period("M")
    if mes_ref not in ipc.index:
        raise ValueError(f"El mes de referencia {mes_ref} no esta en el IPC.")
    idx_mes = df["mes"].map(ipc)
    sin_ipc = int(idx_mes.isna().sum())
    df["valor_real"] = df["valor"] * ipc[mes_ref] / idx_mes
    bit.anotar(f"5. Deflactar a pesos de {mes_ref}", len(df), len(df),
               f"({sin_ipc:,} ventas sin IPC)")
    return df


# ----------------------------------------------------- variables sin fuga
def agregar_historial(df):
    """Variables calculadas solo con ventas anteriores a cada venta.

    Como ya no hay dos filas del mismo predio en la misma fecha, ordenar por
    (predio, fecha) y desplazar una posicion garantiza que cada fila solo ve el pasado.
    """
    df = df.sort_values(["predio_id", "fecha", "pk"], kind="mergesort").reset_index(drop=True)
    g = df.groupby("predio_id", sort=False)
    df["n_ventas_previas"] = g.cumcount()
    df["dias_desde_ultima"] = (df["fecha"] - g["fecha"].shift(1)).dt.days
    df["valor_real_prev"] = g["valor_real"].shift(1)
    return df


def agregar_actividad_zona(df):
    """Ventas de la zona en el mes anterior y promedio de los 3 meses anteriores.

    Se usa solo el pasado (meses completos ya cerrados), asi no se filtra el futuro.
    """
    df["_m"] = indice_mes(df["mes"])
    cuentas = df.groupby(["zona", "_m"]).size().rename("n").reset_index()
    partes = []
    for zona, sub in cuentas.groupby("zona"):
        serie = sub.set_index("_m")["n"].reindex(
            range(sub["_m"].min(), sub["_m"].max() + 1), fill_value=0)
        res = pd.DataFrame({
            "zona": zona,
            "_m": serie.index,
            "ventas_zona_mes_ant": serie.shift(1).values,
            "ventas_zona_3m_ant": serie.shift(1).rolling(3, min_periods=3).mean().values,
        })
        partes.append(res)
    act = pd.concat(partes, ignore_index=True)
    df = df.merge(act, on=["zona", "_m"], how="left").drop(columns="_m")
    return df


# --------------------------------------------------------------------- main
COLUMNAS = ["pk", "predio_id", "zona", "orip", "fecha", "anio", "mes",
            "tipo_predio_zona", "categoria_ruralidad_2024",
            "valor", "valor_real", "n_registros_dia",
            "n_ventas_previas", "dias_desde_ultima", "valor_real_prev",
            "ventas_zona_mes_ant", "ventas_zona_3m_ant"]


def construir(ruta_registro, ruta_ipc, mes_ref=None):
    bit = Bitacora()
    ipc = cargar_ipc(ruta_ipc)
    mes_ref = pd.Period(mes_ref, "M") if mes_ref else ipc.index.max()
    df = pd.read_csv(ruta_registro, dtype={"pk": str, "matricula": str, "orip": str},
                     low_memory=False)
    df = limpiar(df, ipc, mes_ref, bit)
    df = agregar_historial(df)
    df = agregar_actividad_zona(df)
    df["anio"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    out = df[COLUMNAS].sort_values(["fecha", "pk"]).reset_index(drop=True)
    bit.anotar("6. Variables de historial y actividad de zona", len(out), len(out))
    return out, bit


def verificar(out):
    """Chequeos de coherencia que deben pasar antes de versionar."""
    assert out["pk"].is_unique, "pk repetido en la salida"
    assert not out.duplicated(["predio_id", "fecha"]).any(), "quedan duplicados predio+fecha"
    con_prev = out["n_ventas_previas"] > 0
    assert (out.loc[con_prev, "dias_desde_ultima"] > 0).all(), "venta previa no es anterior"
    assert out.loc[~con_prev, "valor_real_prev"].isna().all(), "valor previo sin venta previa"
    assert set(out["zona"].unique()) <= {"Norte", "Centro", "Sur"}
    print("Verificaciones: OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registro", default=os.path.join("data", "compraventas_0125_bogota.csv"))
    ap.add_argument("--ipc", default=os.path.join("data", "ipc.csv"))
    ap.add_argument("--salida", default=os.path.join("data", "compraventas_limpio.csv"))
    ap.add_argument("--resumen", default=os.path.join("reports", "limpieza_resumen.csv"))
    ap.add_argument("--mes-ref", default=None, help="mes de referencia AAAA-MM (por defecto, ultimo mes del IPC)")
    a = ap.parse_args()

    out, bit = construir(a.registro, a.ipc, a.mes_ref)
    verificar(out)
    os.makedirs(os.path.dirname(a.salida) or ".", exist_ok=True)
    out.to_csv(a.salida, index=False)
    bit.guardar(a.resumen)

    con_valor = out["valor"].notna()
    print(f"\nSalida: {a.salida} ({len(out):,} filas, {out.shape[1]} columnas)")
    print(f"Con valor valido: {con_valor.sum():,} | con historial previo: {(out['n_ventas_previas'] > 0).sum():,}")
    print(f"Resumen de pasos: {a.resumen}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
