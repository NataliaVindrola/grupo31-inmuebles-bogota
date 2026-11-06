"""Pantalla 3: rango de una oferta. El usuario elige zona y año, escribe el precio y ve el rango esperado (p10, mediana y p90)."""
import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

import servicios

dash.register_page(__name__, path="/oferta", name="3. Rango de una oferta")
ANIOS = servicios.anios_disponibles() or [2021, 2022, 2023]
COLOR_ESTADO = {"por debajo del rango": "#b45309", "dentro del rango": "#15803d", "por encima del rango": "#b91c1c"}


def layout(zona="Norte", anio=None, precio=None, **_):
    """Acepta valores iniciales por URL, por ejemplo /oferta?zona=Sur&anio=2022&precio=400."""
    zona = zona if zona in servicios.ZONAS else "Norte"
    anio = int(anio) if anio and str(anio).isdigit() and int(anio) in ANIOS else ANIOS[-1]
    precio = float(precio) if precio else 450
    return html.Div([
        html.H3("¿El precio de la oferta está dentro de lo habitual?"),
        html.P("Compara el precio con los valores registrados en la zona y el año elegidos, en millones de pesos constantes.", className="nota"),
        html.Div([
            html.Div([html.Label("Zona registral"), dcc.Dropdown(servicios.ZONAS, zona, id="oferta-zona", clearable=False)]),
            html.Div([html.Label("Año de referencia"), dcc.Dropdown(ANIOS, anio, id="oferta-anio", clearable=False)]),
            html.Div([html.Label("Precio de la oferta (M$ constantes)"), dcc.Input(id="oferta-precio", type="number", value=precio, min=0, debounce=True)]),
        ], className="controles"),
        html.Div(id="oferta-resultado"),
    ])


@callback(Output("oferta-resultado", "children"), Input("oferta-zona", "value"), Input("oferta-anio", "value"), Input("oferta-precio", "value"))
def mostrar(zona, anio, precio):
    if precio is None:
        return html.P("Escribe un precio para compararlo con el rango histórico.", className="nota")
    r = servicios.rango_oferta(zona, anio, float(precio))
    if r is None:
        return html.P("Faltan las tablas del tablero (ejecutar python -m src.tablas).", className="aviso")
    fig = go.Figure()
    fig.add_shape(type="line", x0=r["p10"], x1=r["p90"], y0=0, y1=0, line={"color": "#9fb4c7", "width": 6}, layer="below")
    fig.add_shape(type="line", x0=r["p25"], x1=r["p75"], y0=0, y1=0, line={"color": "#2a6f97", "width": 16}, layer="below")
    fig.add_scatter(x=[r["p50"]], y=[0], mode="markers", marker={"symbol": "line-ns", "size": 28, "line": {"width": 3, "color": "black"}}, name="Mediana",
                    hovertemplate="Mediana %{x:,.0f} M$<extra></extra>")
    fig.add_scatter(x=[precio], y=[0], mode="markers", marker={"symbol": "diamond", "size": 20, "color": COLOR_ESTADO[r["estado"]], "line": {"width": 1, "color": "white"}},
                    name="Oferta", hovertemplate="Oferta %{x:,.0f} M$<extra></extra>")
    for x, t in ((r["p10"], "p10"), (r["p50"], "mediana"), (r["p90"], "p90")):
        fig.add_annotation(x=x, y=0, text=f"{t}<br>{x:,.0f}", yshift=-42, showarrow=False, font={"size": 11})
    fig.update_layout(height=190, margin={"l": 20, "r": 20, "t": 10, "b": 40}, showlegend=False, plot_bgcolor="white",
                      xaxis={"title": f"Millones de pesos de {r['mes_ref']}", "range": [0, max(r["p90"], precio) * 1.1], "gridcolor": "#e7ebf0"},
                      yaxis={"visible": False, "range": [-1, 1]})
    n_txt = f"{r['n']:,}".replace(",", ".")
    return html.Div([
        html.Div(f"La oferta de {precio:,.0f} M$ está {r['estado']}.", className="veredicto", style={"borderColor": COLOR_ESTADO[r["estado"]], "color": COLOR_ESTADO[r["estado"]]}),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.P(f"Rango esperado en {zona}, {anio}: p10 {r['p10']:,.0f} · mediana {r['p50']:,.0f} · p90 {r['p90']:,.0f} M$ "
               f"(barra gruesa: p25 a p75). Se basa en {n_txt} compraventas con valor registradas ese año.", className="nota"),
        html.P("Referencia histórica de valores registrados, no un avalúo. Un precio fuera del rango no implica fraude ni mala oferta.", className="nota"),
    ])
