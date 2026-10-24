"""Reconstruye un indice mensual de precios (base dic-2018 = 100) a partir de la
inflacion total anual (Banco de la Republica). NO es el indice oficial del DANE.

Metodo: la inflacion anual del mes t es I_t / I_(t-12) - 1, asi que
I_t = I_(t-12) * (1 + pi_t). Se necesitan 12 valores iniciales: se toma enero-dic 2013
y se supone crecimiento mensual constante dentro de ese ano, con la tasa anual de dic-2013.
Entrada:  data/ipc.csv (columnas DateTime;Inflacion total anual, coma decimal)
Salida:   data/ipc.csv (columnas fecha,indice); la original queda en data/ipc_original.csv
"""
import os
import pandas as pd

RUTA = os.path.join("data", "ipc.csv")
RESPALDO = os.path.join("data", "ipc_original.csv")
INICIO = "2013-01"
BASE = "2018-12"

if os.path.exists(RESPALDO):
    raw = pd.read_csv(RESPALDO, sep=";", decimal=",", encoding="utf-8-sig")
else:
    raw = pd.read_csv(RUTA, sep=";", decimal=",", encoding="utf-8-sig")
    raw.to_csv(RESPALDO, index=False, sep=";", decimal=",", encoding="utf-8-sig")

raw.columns = ["fecha", "inflacion"]
raw["fecha"] = pd.to_datetime(raw["fecha"], format="%d/%m/%Y")
raw["mes"] = raw["fecha"].dt.to_period("M")
tasa = raw.drop_duplicates("mes").set_index("mes")["inflacion"].sort_index() / 100
tasa = tasa[tasa.index >= pd.Period(INICIO)]

meses = pd.period_range(tasa.index.min(), tasa.index.max(), freq="M")
if len(meses) != len(tasa):
    raise ValueError("La serie tiene meses faltantes; revisar el archivo original.")

idx = pd.Series(index=meses, dtype=float)
r0 = tasa.iloc[11]                       # inflacion anual de dic del primer ano
for k in range(12):
    idx.iloc[k] = 100 * (1 + r0) ** ((k + 1) / 12)
for t in range(12, len(idx)):
    idx.iloc[t] = idx.iloc[t - 12] * (1 + tasa.iloc[t])

idx = idx / idx[pd.Period(BASE)] * 100   # base dic-2018 = 100
out = pd.DataFrame({"fecha": idx.index.to_timestamp(how="end").normalize(),
                    "indice": idx.round(4).values})
out["fecha"] = out["fecha"].dt.strftime("%Y-%m-%d")
out.to_csv(RUTA, index=False)
print(out.head(3)); print(out.tail(3)); print(f"{len(out)} meses, {out.fecha.iloc[0]} a {out.fecha.iloc[-1]}")
