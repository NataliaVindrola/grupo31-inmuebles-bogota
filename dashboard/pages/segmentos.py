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
    z = df.pivot(index="zona", columns="q", values="mediana_real").reindex(servicios.ZONAS)
    n = df.pivot(index="zona", columns="q", values="n").reindex(servicios.ZONAS)
    ic = (df.assign(t=lambda d: d["ic_inf"].map("{:.1%}".format) + " a " + d["ic_sup"].map("{:.1%}".format))
            .pivot(index="zona", columns="q", values="t").reindex(servicios.ZONAS))
    rango = df.drop_duplicates("q").set_index("q")
    etiquetas = [f"Q{q}<br>{rango.loc[q, 'rango_min_musd']:.0f}–{rango.loc[q, 'rango_max_musd']:.0f} M$" for q in z.columns]
    texto = [[f"{z.iloc[i, j]:+.1%}<br>n={int(n.iloc[i, j])}" + ("" if n.iloc[i, j] >= 100 else "*") for j in range(z.shape[1])]
             for i in range(z.shape[0])]
    hover = [[f"{z.index[i]} · Q{z.columns[j]}<br>Mediana {z.iloc[i, j]:+.1%}<br>Intervalo 90 %: {ic.iloc[i, j]}<br>n = {int(n.iloc[i, j])}"
              for j in range(z.shape[1])] for i in range(z.shape[0])]
    lim = float(abs(z.values).max())
    fig = go.Figure(go.Heatmap(z=z.values, x=etiquetas, y=list(z.index), text=texto, texttemplate="%{text}", hovertext=hover, hoverinfo="text",
                               colorscale="RdYlGn", zmid=0, zmin=-lim, zmax=lim, colorbar={"tickformat": ".0%", "title": "Retorno real"}))
    fig.update_layout(height=340, margin={"l": 60, "r": 20, "t": 20, "b": 60}, yaxis={"autorange": "reversed"}, paper_bgcolor="white")
    suf = df[df["suficiente"]]
    mejor, peor = suf.loc[suf["mediana_real"].idxmax()], suf.loc[suf["mediana_real"].idxmin()]
    kpi = lambda t, v: html.Div([html.Span(t, className="kpi-t"), html.Span(v, className="kpi-v")], className="kpi")
    return html.Div([
        html.H3("¿Dónde concentrar la búsqueda? Retorno real anualizado por segmento"),
        html.P("Mediana del retorno real anual (descontando la inflación) de predios revendidos, por zona registral y rango de valor de la "
               "primera venta (quintiles, millones de pesos constantes). Al pasar el cursor se ve el intervalo del 90 %.", className="nota"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Div([
            kpi("Mayor valorización (n ≥ 100)", f"{mejor['zona']} Q{int(mejor['q'])}: {mejor['mediana_real']:+.1%}"),
            kpi("Menor valorización (n ≥ 100)", f"{peor['zona']} Q{int(peor['q'])}: {peor['mediana_real']:+.1%}"),
            kpi("Pares de ventas repetidas", f"{int(df['n'].sum()):,}".replace(",", ".")),
        ], className="kpis"),
        html.P("* Menos de 100 pares: no concluyente. La valorización cubre solo 2022 y 2023, porque el valor existe en el registro desde 2021. "
               "Referencia histórica, no un avalúo ni una recomendación de compra.", className="nota"),
    ])
