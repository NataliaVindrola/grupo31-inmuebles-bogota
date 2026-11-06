"""Pantalla 2: liquidez, probabilidad de reventa por zona (Kaplan-Meier) y valores a 1, 3 y 5 años."""
import dash
import plotly.graph_objects as go
from dash import dcc, html

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
    ])
