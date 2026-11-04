"""Pantalla 1: segmentos zona x rango de valor (retorno real anualizado, intervalo del 90 % y n)."""
import dash
import plotly.graph_objects as go
from dash import dcc, html

import servicios

dash.register_page(__name__, path="/", name="1. Segmentos")


def layout(**_):
    df = servicios.tabla("segmentos")
    if df is None:
        return html.Div("Falta dashboard/data/segmentos.csv (ejecutar python -m src.tablas).", className="aviso")
    mat = df.pivot(index="zona", columns="q", values="mediana_real")
    texto = df.assign(t=lambda d: d["mediana_real"].map("{:+.1%}".format) + "<br>n=" + d["n"].astype(str)).pivot(index="zona", columns="q", values="t")
    fig = go.Figure(go.Heatmap(z=mat.values, x=[f"Q{q}" for q in mat.columns], y=mat.index, text=texto.values,
                               texttemplate="%{text}", colorscale="RdYlGn", zmid=0))
    return html.Div([
        html.H3("¿Dónde concentrar la búsqueda? Retorno real anualizado por segmento"),
        dcc.Graph(figure=fig),
        html.P("Los segmentos con menos de 100 pares son no concluyentes. La valorización cubre solo 2022 y 2023.", className="nota"),
    ])
