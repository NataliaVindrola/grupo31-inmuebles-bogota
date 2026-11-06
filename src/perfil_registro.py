"""
perfil_registro.py - Perfil de calidad del registro de compraventas de Bogota.

Uso (desde la raiz del proyecto):
    python src/perfil_registro.py
    python src/perfil_registro.py data/compraventas_0125_bogota.csv

Imprime, para escribir datos.py sin suponer nada:
  1. Cuantas compraventas hay por codigo de ORIP (para saber cual es Norte/Centro/Sur).
  2. Formatos de fecha presentes y si el anio de la fecha coincide con year_radica.
  3. Cobertura del valor por anio (vacio o cero).
  4. Duplicados: por pk, por matricula+fecha y por matricula+fecha+valor.
  5. Formato de la matricula y cuantos predios tienen mas de una compraventa.

La salida sirve tambien como evidencia de calidad de datos (Guia 4).
"""
import re
import sys

import pandas as pd

RUTA = "data/compraventas_0125_bogota.csv"
RE_CORTA = r"^\d{1,2}/\d{1,2}/\d{2}$"
RE_ISO = r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}:\d{2}(\.\d+)?)?$"


def parsear_fechas(serie):
    """Convierte los dos formatos conocidos; devuelve (fecha, formato)."""
    s = serie.astype(str).str.strip()
    corta = s.str.match(RE_CORTA)
    iso = s.str.match(RE_ISO)
    fecha = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    fecha[corta] = pd.to_datetime(s[corta], format="%d/%m/%y", errors="coerce")
    fecha[iso] = pd.to_datetime(s[iso], errors="coerce")
    formato = pd.Series("otro", index=s.index)
    formato[corta] = "dd/mm/aa"
    formato[iso] = "ISO (aaaa-mm-dd ...)"
    formato[serie.isna()] = "vacio"
    return fecha, formato


def titulo(t):
    print("\n" + t)
    print("-" * len(t))


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA
    df = pd.read_csv(ruta, low_memory=False)
    n = len(df)
    print(f"Archivo: {ruta}")
    print(f"Filas: {n:,} | Columnas: {list(df.columns)}")

    titulo("1. Compraventas por codigo de ORIP")
    print(df["orip"].value_counts(dropna=False).sort_index().to_string())

    titulo("2. Fechas")
    fecha, formato = parsear_fechas(df["fecha_radica_texto"])
    print(formato.value_counts().to_string())
    print(f"No convertidas: {fecha.isna().sum():,}")
    ok = fecha.dt.year == df["year_radica"]
    print(f"Anio de la fecha = year_radica: {ok.mean():.2%} ({(~ok).sum():,} filas no coinciden)")

    titulo("3. Valor por anio de radicacion")
    v = pd.to_numeric(df["valor"], errors="coerce")
    tab = pd.DataFrame({
        "n": df.groupby("year_radica").size(),
        "con_valor": (v.notna() & (v > 0)).groupby(df["year_radica"]).sum(),
        "valor_cero": (v == 0).groupby(df["year_radica"]).sum(),
    })
    tab["pct_con_valor"] = (tab["con_valor"] / tab["n"]).round(3)
    print(tab.to_string())
    print(f"Valor vacio en total: {v.isna().sum():,} | valor < 5 millones: {((v > 0) & (v < 5e6)).sum():,}")

    titulo("4. Duplicados")
    print(f"pk repetido: {df['pk'].duplicated().sum():,}")
    k1 = df["matricula"].astype(str) + "|" + fecha.dt.strftime("%Y-%m-%d").fillna("NA")
    k2 = k1 + "|" + v.fillna(-1).round().astype("int64").astype(str)
    print(f"matricula + fecha repetidas: {k1.duplicated().sum():,} filas sobrantes")
    print(f"matricula + fecha + valor repetidas: {k2.duplicated().sum():,} filas sobrantes")
    print("(Esas filas son la misma venta registrada mas de una vez; datos.py las colapsa.)")

    titulo("5. Matricula y predios con varias compraventas")
    m = df["matricula"].astype(str).str.strip()
    print("Formato de matricula:")
    print(m.str.replace(r"\d", "9", regex=True).str.replace(r"9+", "9", regex=True)
          .value_counts().head(5).to_string())
    por_predio = m.groupby(m).size()
    print(f"Predios distintos: {por_predio.size:,} | con 2+ filas: {(por_predio >= 2).sum():,}")
    llave = df["orip"].astype(str) + "|" + m
    print(f"Llave orip+matricula distinta: {llave.nunique():,}")
    


if __name__ == "__main__":
    main()
