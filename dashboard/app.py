"""Tablero del Grupo 31 (Dash). Tres pantallas, según mockup/mockup_tablero.html.

Responsable: Jorge. Uso, desde la raíz del repositorio:   python dashboard/app.py   (http://localhost:8050)
Las pantallas están en dashboard/pages/ (una por archivo) y leen las tablas de dashboard/data/ (las genera `python -m src.tablas`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # raíz del repositorio, para `from src import ...`

import dash
from dash import Dash, dcc, html

app =Dash(__name__, use_pages=True, pages_folder="pages", title="Grupo 31 · Referencia histórica de valores en Bogotá")
server = app.server  # para gunicorn y Docker más adelante

app.layout = html.Div(
    className="app",
    children=[
        html.Header("Referencia histórica de valores de compraventas en Bogotá · Grupo 31"),
        html.Nav(
            [dcc.Link(p["name"], href=p["relative_path"], className="tab") for p in dash.page_registry.values()]
        ),
        dash.page_container,
        html.Footer("Referencia histórica de valores registrados 2021-2023. No es un avalúo ni una recomendación de compra."),
    ],
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
