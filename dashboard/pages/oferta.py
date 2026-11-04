"""Pantalla 3: rango de una oferta. El usuario elige zona y año, escribe el precio y ve el rango esperado (p10, mediana y p90)."""
import dash
from dash import Input, Output, callback, dcc, html

import servicios

dash.register_page(__name__, path="/oferta", name="3. Rango de una oferta")


def layout(**_):
    return html.Div([
        html.H3("¿El precio de la oferta está dentro de lo habitual?"),
        html.Div([
            dcc.Dropdown(["Norte", "Centro", "Sur"], "Norte", id="oferta-zona", clearable=False),
            dcc.Dropdown([2021, 2022, 2023], 2023, id="oferta-anio", clearable=False),
            dcc.Input(id="oferta-precio", type="number", placeholder="Precio de la oferta (millones de pesos constantes)", min=0),
        ], className="controles"),
        html.Div(id="oferta-resultado"),
    ])


@callback(Output("oferta-resultado", "children"), Input("oferta-zona", "value"), Input("oferta-anio", "value"), Input("oferta-precio", "value"))
def mostrar(zona, anio, precio):
    if precio is None:
        return html.P("Escribe un precio para compararlo con el rango histórico.", className="nota")
    r = servicios.rango_oferta(zona, anio, float(precio))
    if r is None:
        return html.P("El modelo de rango todavía no está disponible (models/rango/v1).", className="aviso")
    return html.Div([
        html.P(f"Rango esperado en {zona}: p10 {r['p10']:.0f} · mediana {r['p50']:.0f} · p90 {r['p90']:.0f} millones de pesos constantes."),
        html.P(f"La oferta de {precio:,.0f} está {r['estado']}.", className="resultado"),
        html.P("Referencia histórica de valores registrados, no un avalúo.", className="nota"),
    ])
