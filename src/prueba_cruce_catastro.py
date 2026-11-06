"""
prueba_cruce_catastro.py - Prueba rapida: que porcentaje de las compraventas del
registro (IGAC-SNR) se puede cruzar con el catastro de Bogota por matricula.

Uso (desde la raiz del proyecto):
    python src/prueba_cruce_catastro.py data/raw/tpredio.csv.08.26.zip

Que hace:
  1. Lee SOLO el encabezado del CSV del catastro y lo imprime (captura para el reporte).
  2. Busca la columna de matricula (nombre que contenga 'matric').
  3. Arma la misma llave en las dos fuentes: ORIP + numero de matricula
     (ej. 50C1346790), sin guiones ni ceros a la izquierda.
  4. Imprime el porcentaje de compraventas que cruzan, en total, por ORIP y por anio.

Si el catastro NO trae columna de matricula, el script lo dice y se detiene:
en ese caso el cruce por matricula no es posible con este archivo.

Opciones por si los nombres de columna no se detectan solos:
    --col-mat-cat NOMBRE     columna de matricula en el catastro
    --col-mat-reg NOMBRE     columna de matricula en el registro
    --col-orip-reg NOMBRE    columna de ORIP en el registro
    --col-anio-reg NOMBRE    columna del anio en el registro
"""
import argparse
import re
import sys
import unicodedata

import pandas as pd

REGISTRO = "data/compraventas_0125_bogota.csv"


def norm(texto):
    """Minusculas y sin tildes, para comparar nombres de columnas."""
    t = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def buscar_col(columnas, *claves, excluir=()):
    for c in columnas:
        n = norm(c)
        if all(k in n for k in claves) and not any(e in n for e in excluir):
            return c
    return None


def llave_desde_texto(serie):
    """'50C-1346790' / '50C1346790' / '050C 01346790' -> '50C1346790'."""
    s = serie.astype(str).str.upper().str.replace(r"[^0-9A-Z]", "", regex=True)
    m = s.str.extract(r"^0*(50[NCS])0*(\d+)$")
    llave = m[0] + m[1]
    return llave


def llave_registro(df, col_orip, col_mat):
    orip = df[col_orip].astype(str).str.upper().str.replace(r"[^0-9A-Z]", "", regex=True)
    num = df[col_mat].astype(str).str.replace(r"\D", "", regex=True).str.lstrip("0")
    llave = orip + num
    llave[num == ""] = pd.NA
    return llave


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("catastro", help="CSV (o ZIP con un CSV) de Predios Bogota")
    ap.add_argument("--registro", default=REGISTRO)
    ap.add_argument("--col-mat-cat")
    ap.add_argument("--col-mat-reg")
    ap.add_argument("--col-orip-reg")
    ap.add_argument("--col-anio-reg")
    ap.add_argument("--sep", default=None, help="separador del CSV del catastro (por defecto se detecta)")
    ap.add_argument("--encoding", default="utf-8")
    a = ap.parse_args()

    # 1) Encabezado del catastro
    try:
        enc = pd.read_csv(a.catastro, nrows=0, sep=a.sep, engine="python",
                          encoding=a.encoding)
    except UnicodeDecodeError:
        a.encoding = "latin-1"
        enc = pd.read_csv(a.catastro, nrows=0, sep=a.sep, engine="python",
                          encoding=a.encoding)
    print(f"\nColumnas del catastro ({len(enc.columns)}):")
    for c in enc.columns:
        print("  -", c)

    col_cat = a.col_mat_cat or buscar_col(enc.columns, "matric")
    if col_cat is None:
        print("\nRESULTADO: el catastro NO trae una columna de matricula.")
        print("El cruce por matricula no es posible con este archivo.")
        print("Revisa si hay otra columna que identifique el predio (por ejemplo")
        print("un codigo de lote o CHIP) y si el registro tiene un equivalente.")
        sys.exit(2)
    print(f"\nColumna de matricula en el catastro: {col_cat}")

    # 2) Registro
    reg = pd.read_csv(a.registro, low_memory=False)
    col_mat_reg = a.col_mat_reg or buscar_col(reg.columns, "matric")
    col_orip = a.col_orip_reg or buscar_col(reg.columns, "orip")
    col_anio = a.col_anio_reg or buscar_col(reg.columns, "anio") or buscar_col(reg.columns, "ano") \
        or buscar_col(reg.columns, "radic", "a")
    print(f"Registro: matricula={col_mat_reg} | orip={col_orip} | anio={col_anio}")
    if col_mat_reg is None or col_orip is None:
        print("No pude detectar las columnas del registro. Columnas disponibles:")
        print(list(reg.columns))
        print("Usa --col-mat-reg y --col-orip-reg.")
        sys.exit(1)

    reg["_llave"] = llave_registro(reg, col_orip, col_mat_reg)

    # 3) Llaves del catastro (solo la columna de matricula, para ahorrar memoria)
    cat = pd.read_csv(a.catastro, usecols=[col_cat], sep=a.sep, engine="python",
                      encoding=a.encoding, dtype=str)
    llaves_cat = llave_desde_texto(cat[col_cat]).dropna()
    print(f"\nFilas en catastro: {len(cat):,} | con matricula valida: {len(llaves_cat):,} "
          f"| matriculas unicas: {llaves_cat.nunique():,}")
    if len(llaves_cat) == 0:
        print("Ninguna matricula del catastro tiene el formato ORIP+numero (50N/50C/50S).")
        print("Muestra de valores:", cat[col_cat].dropna().head(5).tolist())
        sys.exit(3)

    reg["_cruza"] = reg["_llave"].isin(set(llaves_cat))
    n = len(reg)
    print(f"\nCompraventas del registro: {n:,}")
    print(f"  con llave valida: {reg['_llave'].notna().sum():,} ({reg['_llave'].notna().mean():.1%})")
    print(f"  que cruzan con el catastro: {reg['_cruza'].sum():,} ({reg['_cruza'].mean():.1%})")

    print("\nPor ORIP:")
    print(reg.groupby(col_orip)["_cruza"].agg(["size", "mean"]).rename(
        columns={"size": "n", "mean": "pct_cruce"}).round(3).to_string())
    if col_anio is not None:
        print("\nPor anio:")
        print(reg.groupby(col_anio)["_cruza"].agg(["size", "mean"]).rename(
            columns={"size": "n", "mean": "pct_cruce"}).round(3).to_string())

    print("\nMuestra de llaves (registro):", reg["_llave"].dropna().head(3).tolist())
    print("Muestra de llaves (catastro):", llaves_cat.head(3).tolist())


if __name__ == "__main__":
    main()
