"""Pantalla 2: liquidez, probabilidad de reventa por zona (Kaplan-Meier) y valores a 1, 3 y 5 años, y la probabilidad de reventa
a 3 años que estima el modelo de reventa (models/reventa/v1) para un predio."""
import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

import servicios

dash.register_page(__name__, path="/liquidez", name="2. Liquidez")
COLORES = {"Norte": "#2a6f97", "Centro": "#e07a5f", "Sur": "#3d9970"}


def layout(**_):
    df, res = servicios.tabla("liquidez"), servicios.tabla("liquidez_resumen")
    if df is None or res is None:
        return html.Div("Falta dashboard/data/liquidez.csv (ejecutar python -m src.tablas).", className="aviso")
    fig = go.Figure()
    for zona in servicios.ZONAS:
        d = df[df["zona"] == zona]
        fig.add_scatter(x=d["anios"], y=d["prob_reventa"], mode="lines", name=f"{zona} (n={int(d['n'].iloc[0]):,})".replace(",", "."),
                        line={"color": COLORES[zona], "width": 3, "shape": "hv"}, hovertemplate="%{x:.1f} años: %{y:.1%}<extra>" + zona + "</extra>")
    fig.update_layout(height=340, margin={"l": 60, "r": 20, "t": 20, "b": 50}, paper_bgcolor="white", plot_bgcolor="white",
                      xaxis={"title": "Años desde la compra", "gridcolor": "#e7ebf0"}, yaxis={"title": "Probabilidad acumulada de reventa", "tickformat": ".0%", "gridcolor": "#e7ebf0"},
                      legend={"orientation": "h", "y": 1.12})
    filas = [html.Tr([html.Th(c) for c in ("Zona", "A 1 año", "A 3 años", "A 5 años", "Compraventas")])]
    for zona in servicios.ZONAS:
        r = res[res["zona"] == zona].iloc[0]
        filas.append(html.Tr([html.Td(zona), html.Td(f"{r['prob_1a']:.1%}"), html.Td(f"{r['prob_3a']:.1%}"), html.Td(f"{r['prob_5a']:.1%}"), html.Td(f"{int(r['n']):,}".replace(",", "."))]))
    return html.Div([
        html.H3("¿Podré vender sin esperar años? Probabilidad de reventa por zona"),
        html.P("Curvas de Kaplan-Meier con las compraventas de 2015 a 2023; los predios que aún no se revenden se tratan como censurados.", className="nota"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Table(filas, className="tabla"),
        html.P("Las diferencias entre zonas son de uno o dos puntos y el orden entre Norte y Sur cambia según la cohorte de compra: "
               "se presenta como orden de magnitud, no como un ranking fino.", className="nota"),
        html.H4("Probabilidad de reventa a 3 años de un predio (modelo)"),
        html.Div([
            html.Div([html.Label("Zona registral"), dcc.Dropdown(servicios.ZONAS, "Norte", id="liq-zona", clearable=False)]),
            html.Div([html.Label("Tipo de predio"), dcc.Dropdown(servicios.TIPOS_PREDIO, "URBANO", id="liq-tipo", clearable=False)]),
            html.Div([html.Label("Ventas previas del predio desde 2015"), dcc.Input(id="liq-previas", type="number", value=0, min=0, max=20, step=1, debounce=True)]),
        ], className="controles"),
        html.Div(id="liq-resultado"),
    ])


@callback(Output("liq-resultado", "children"), Input("liq-zona", "value"), Input("liq-tipo", "value"), Input("liq-previas", "value"))
def estimar(zona, tipo, previas):
    p = servicios.prob_reventa_modelo(zona, tipo, previas or 0)
    if p is None:
        return html.P("La estimación aparecerá cuando exista models/reventa/v1 (experimentos/train_reventa.py --guardar-version v1).", className="aviso")
    res = servicios.tabla("liquidez_resumen")
    zona_3a = float(res.loc[res["zona"] == zona, "prob_3a"].iloc[0]) if res is not None else None
    ref = f" La curva de la zona da {zona_3a:.1%} a 3 años." if zona_3a is not None else ""
    return html.Div([
        html.Div([html.Span("Probabilidad estimada de reventa en 3 años", className="kpi-t"), html.Span(f"{p:.1%}", className="kpi-v")], className="kpi"),
        html.P(f"Modelo de gradient boosting con zona, tipo de predio, mes de compra y ventas previas.{ref} "
               "En la validación temporal (compras 2018-2020) su AUC apenas supera a la tasa por zona: es una referencia, no un pronóstico del predio.",
               className="nota"),
    ])
