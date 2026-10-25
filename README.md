# Grupo 31 - Referencia historica de valores de compraventas en Bogota
Proyecto MIAD - Despliegue de soluciones analiticas.
Integrantes: Julian David Zapata Valencia, Jorge Felipe Alarcon Torres, Natalia Vindrola Munoz.

## Contenido
- `data/`: archivos `.dvc` de los datos (compraventas de Bogota 2015-2023, IPC). Los datos viven en el remoto DVC de DagsHub.
- `notebooks/`: `01_exploracion_bogota.ipynb` (exploracion) y `02_valorizacion_liquidez_modelo.ipynb` (valorizacion, liquidez y validacion de modelos).
- `src/`: `construir_ipc.py` reconstruye el indice de precios a partir de la inflacion anual.
- `reports/figures/`: figuras y cifras clave de los notebooks.
- `mockup/`: maqueta del tablero (HTML interactivo e imagen).

## Reproducir los datos
```
git clone https://github.com/NataliaVindrola/grupo31-inmuebles-bogota
cd grupo31-inmuebles-bogota
dvc pull
```
