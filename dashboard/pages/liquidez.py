"""Pantalla 2: liquidez, probabilidad de reventa por zona (Kaplan-Meier) y valores a 1, 3 y 5 años."""
import dash
import plotly.express as px
from dash import dcc, html

import servicios

dash.register_page(__name__, path="/liquidez", name="2. Liquidez")


def layout(**_):
    df = servicios.tabla("liquidez")
    if df is None:
        return html.Div("Falta dashboard/data/liquidez.csv (ejecutar python -m src.tablas).", className="aviso")
    fig = px.line(df, x="anios", y="prob_reventa", color="zona", labels={"anios": "Años desde la compra", "prob_reventa": "Probabilidad de reventa"})
    fig.update_yaxes(tickformat=".0%")
    return html.Div([
        html.H3("¿Podré vender sin esperar años? Probabilidad de reventa por zona"),
        dcc.Graph(figure=fig),
        html.P("Las diferencias entre zonas son de uno o dos puntos y el orden entre Norte y Sur cambia según la cohorte de compra.", className="nota"),
    ])
