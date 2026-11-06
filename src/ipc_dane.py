"""
ipc_dane.py - Convierte el anexo oficial del DANE (IPC total nacional, serie de
empalme, base dic-2018 = 100) al formato del proyecto: data/ipc.csv con las
columnas `fecha` e `indice`.

Uso (desde la raiz del proyecto):
    python src/ipc_dane.py data/raw/anex-IPC-Indices-sep2026.xlsx

Opciones:
    --desde 2013-01   primer mes a conservar
    --hasta 2026-09   ultimo mes a conservar (mes de referencia del proyecto)

Si ya existe data/ipc.csv, se respalda como data/ipc_reconstruido.csv
(solo la primera vez), para conservar el indice reconstruido de la Entrega 1.
"""
import argparse
import os
import shutil
import sys

import pandas as pd

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
FECHA_BASE = "2018-12"


def leer_ipc_dane(ruta_xlsx, desde="2013-01", hasta="2026-09"):
    """Lee la hoja del DANE (meses en filas, anios en columnas) y devuelve
    un DataFrame largo con columnas fecha (fin de mes) e indice."""
    bruto = pd.read_excel(ruta_xlsx, sheet_name=0, header=None)

    # La fila de encabezado es la que dice "Mes" en la primera columna.
    filas_mes = bruto.index[bruto[0].astype(str).str.strip().str.lower() == "mes"]
    if len(filas_mes) == 0:
        raise ValueError("No encontre la fila de encabezado 'Mes'. "
                         "Revisa que sea el anexo de indices del DANE.")
    fila_enc = filas_mes[0]
    anios = bruto.iloc[fila_enc, 1:]
    registros = []
    for i in range(fila_enc + 1, len(bruto)):
        nombre = str(bruto.iloc[i, 0]).strip().lower()
        if nombre not in MESES:
            continue
        for col, anio in anios.items():
            valor = bruto.iloc[i, col]
            if pd.isna(anio) or pd.isna(valor):
                continue
            periodo = pd.Period(year=int(anio), month=MESES[nombre], freq="M")
            registros.append((periodo, float(valor)))

    df = pd.DataFrame(registros, columns=["periodo", "indice"]).sort_values("periodo")
    df = df[(df["periodo"] >= pd.Period(desde)) & (df["periodo"] <= pd.Period(hasta))]
    df["fecha"] = df["periodo"].dt.to_timestamp(how="end").dt.normalize()
    df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")
    return df[["fecha", "indice"]].reset_index(drop=True)


def validar(df, desde, hasta):
    """Chequeos que deben pasar antes de usar el indice."""
    esperados = pd.period_range(desde, hasta, freq="M")
    if len(df) != len(esperados):
        faltan = set(esperados.strftime("%Y-%m-%d")) - set(df["fecha"].str[:7] + "-01")
        raise ValueError(f"Se esperaban {len(esperados)} meses y hay {len(df)}.")
    if df["indice"].isna().any() or (df["indice"] <= 0).any():
        raise ValueError("Hay indices vacios o no positivos.")
    base = df.loc[df["fecha"].str.startswith(FECHA_BASE), "indice"]
    if len(base) and abs(float(base.iloc[0]) - 100.0) > 0.01:
        raise ValueError(f"El indice de {FECHA_BASE} deberia ser 100 y es {base.iloc[0]}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xlsx", help="Excel del DANE (anex-IPC-Indices-...xlsx)")
    ap.add_argument("--desde", default="2013-01")
    ap.add_argument("--hasta", default="2026-09")
    ap.add_argument("--salida", default=os.path.join("data", "ipc.csv"))
    args = ap.parse_args()

    df = leer_ipc_dane(args.xlsx, args.desde, args.hasta)
    validar(df, args.desde, args.hasta)

    if os.path.exists(args.salida):
        respaldo = os.path.join(os.path.dirname(args.salida), "ipc_reconstruido.csv")
        if not os.path.exists(respaldo):
            shutil.copy(args.salida, respaldo)
            print(f"Respaldo del indice anterior: {respaldo}")
    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
    df.to_csv(args.salida, index=False)

    print(df.head(3).to_string(index=False))
    print(df.tail(3).to_string(index=False))
    print(f"{len(df)} meses, {df['fecha'].iloc[0]} a {df['fecha'].iloc[-1]} -> {args.salida}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
