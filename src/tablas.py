"""Genera las tablas ya calculadas que lee el tablero (pantallas 1 y 2 y el histórico de la pantalla 3).

Responsable: Natalia (con Julián). Se toma de los notebooks 01 y 02. Uso:  python -m src.tablas
Salida en dashboard/data/ (los nombres y columnas son el CONTRATO con el tablero):

segmentos.csv         zona, q, rango_min_musd, rango_max_musd, n, mediana_real, ic_inf, ic_sup, suficiente (n >= 100)
liquidez.csv          zona, anios, prob_reventa, n                  (curva de Kaplan-Meier por zona, anios de 0 a 9)
liquidez_resumen.csv  zona, prob_1a, prob_3a, prob_5a, n
rango_historico.csv   zona, anio, p10, p25, p50, p75, p90, n        (M$ constantes de MES_REF)
cifras_clave.csv      cifra, valor                                   (ya existe en reports/figures/cifras_clave_02.csv)
"""
from pathlib import Path

SALIDA = Path("dashboard/data")


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
