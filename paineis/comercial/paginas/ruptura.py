"""Página Ruptura: cobertura da carteira (clientes ativos que compraram no mês) por vendedor."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

from paineis.comercial import dados
from paineis.comum import componentes as c
from paineis.comum import exportar, formatos
from paineis.comum.dados import ler_parquet, para_grade

FAIXAS_RUPTURA = [(40, "#c0392b", "crítica"), (30, "#e67e22", "alta"), (20, "#f2a93b", "média"), (0, "#2e8b57", "baixa")]
ESTILO_COBERTURA = {"styleConditions": [
    {"condition": "params.value >= 75", "style": {"color": "#2e8b57", "fontWeight": "700"}},
    {"condition": "params.value < 60", "style": {"color": "#c0392b", "fontWeight": "700"}},
]}
ESTILO_RUPTURA = {"styleConditions": [
    {"condition": f"params.value >= {limite}", "style": {"backgroundColor": cor, "color": "#fff", "fontWeight": "700"}}
    for limite, cor, _ in FAIXAS_RUPTURA[:3]
]}
ESTILO_CAPTACAO = {"styleConditions": [
    {"condition": "params.value > 0", "style": {"color": "#2e8b57", "fontWeight": "700"}},
    {"condition": "params.value < 0", "style": {"color": "#c0392b", "fontWeight": "700"}},
]}
COLUNAS = [
    c.coluna("vendedor", "Vendedor", largura=170, pinned="left"),
    c.coluna("clientes_ativos", "Clientes ativos", "inteiro", largura=130),
    c.coluna("clientes_cobertos", "Com compra", "inteiro", largura=120),
    c.coluna("clientes_sem_compra", "Sem compra", "inteiro", largura=115),
    c.coluna("perc_cobertura", "% cobertura", "pct", largura=120, cellStyle=ESTILO_COBERTURA),
    c.coluna("perc_ruptura", "% ruptura", "pct", largura=110, cellStyle=ESTILO_RUPTURA),
    c.coluna("clientes_inadimplentes", "Inadimplentes", "inteiro", largura=125),
    c.coluna("perc_inadimplencia", "% inadimpl.", "pct", largura=115),
    c.coluna("clientes_novos", "Novos", "inteiro", largura=90),
    c.coluna("clientes_cancelados", "Cancelados", "inteiro", largura=110),
    c.coluna("captacao_liquida", "Captação líq.", "inteiro", largura=120, cellStyle=ESTILO_CAPTACAO),
]


def cor_ruptura(valor):
    return next(cor for limite, cor, _ in FAIXAS_RUPTURA if valor >= limite)


def layout():
    meses = sorted(ler_parquet("ruptura_vendedor_mes")["mes"].unique(), reverse=True)
    return html.Div([
        html.Section(className="secao barra-filtros", children=[
            c.filtro("Vendedor", c.dropdown("cm-r-vendedor", multi=False)),
            c.filtro("Mês", dcc.Dropdown(id="cm-r-mes", options=[{"label": formatos.mes_rotulo(int(m)), "value": int(m)} for m in meses],
                                         value=int(meses[1] if len(meses) > 1 else meses[0]), clearable=False, className="dropdown")),
            html.Span("Ruptura = clientes ativos da carteira sem compra no mês. Abre no último mês fechado; "
                      "o mês corrente, ainda em andamento, também está na lista.", className="nota"),
        ]),
        html.Div(className="graficos", children=[
            html.Section(className="secao", children=[html.H2("Cobertura da carteira"), html.Div(id="cm-r-resumo")]),
            html.Section(className="secao", children=[html.H2("Evolução da cobertura"), dcc.Graph(id="cm-r-cobertura", config={"displayModeBar": False})]),
            html.Section(className="secao", children=[html.H2("Evolução da ruptura"), dcc.Graph(id="cm-r-ruptura", config={"displayModeBar": False})]),
        ]),
        html.Section(className="secao", children=[
            html.Div(className="barra-tabela", children=[
                html.H2(id="cm-r-titulo"),
                html.Button("⬇ Exportar", id="cm-r-exportar", className="botao secundario"),
            ]),
            c.grade("cm-r-grade", COLUNAS, altura=280),
            html.P("Ruptura: até 20% baixa, 20 a 30% média, 30 a 40% alta, 40% ou mais crítica.", className="nota"),
            dcc.Download(id="cm-r-download"),
        ]),
    ])


def _barras(evolucao, coluna, cores):
    rotulos = [formatos.mes_rotulo(int(m)) for m in evolucao["mes"]]
    figura = go.Figure(go.Bar(x=rotulos, y=evolucao[coluna], marker_color=cores,
                              text=[formatos.pct(v, 0) for v in evolucao[coluna]], textposition="outside"))
    figura.update_layout(height=230, margin={"l": 10, "r": 10, "t": 10, "b": 10}, yaxis_visible=False,
                         yaxis_range=[0, max(evolucao[coluna].max() * 1.3, 10)], plot_bgcolor="#fff")
    return figura


def registrar(app):
    @app.callback(Output("cm-r-vendedor", "options"), Input("cm-revenda", "value"))
    def vendedores(revenda):
        df = ler_parquet("ruptura_vendedor_mes")
        nomes = df[df["revenda_id"] == revenda][["vendedor_id", "vendedor"]].drop_duplicates().sort_values("vendedor_id")
        return [{"label": v.vendedor, "value": v.vendedor_id} for v in nomes.itertuples()]

    @app.callback(
        Output("cm-r-resumo", "children"), Output("cm-r-cobertura", "figure"), Output("cm-r-ruptura", "figure"),
        Output("cm-r-grade", "rowData"), Output("cm-r-grade", "dashGridOptions"), Output("cm-r-titulo", "children"),
        Input("cm-revenda", "value"), Input("cm-r-mes", "value"), Input("cm-r-vendedor", "value"),
    )
    def atualizar(revenda, mes, vendedor):
        do_mes, total, evolucao, variacao = dados.ruptura(revenda, mes, vendedor)
        evolucao = evolucao.tail(13)
        rosca = go.Figure(go.Pie(values=[total["clientes_cobertos"], total["clientes_sem_compra"]], labels=["Com compra", "Sem compra"],
                                 hole=0.62, marker_colors=["#0e4d64", "#f2a93b"], sort=False, textinfo="none"))
        rosca.update_layout(height=180, margin={"l": 0, "r": 0, "t": 0, "b": 0}, showlegend=False,
                            annotations=[{"text": formatos.pct(total["perc_cobertura"]), "showarrow": False, "font": {"size": 20}}])
        chip = "Sem comparativo" if variacao is None else f"{'▲' if variacao >= 0 else '▼'} {formatos.numero(abs(variacao), 1)} p.p. vs mês anterior"
        resumo = html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "alignItems": "center"}, children=[
            dcc.Graph(figure=rosca, config={"displayModeBar": False}),
            html.Div([
                html.P(["Clientes ativos: ", html.Strong(formatos.numero(total["clientes_ativos"]))]),
                html.P(["Com compra: ", html.Strong(formatos.numero(total["clientes_cobertos"]))]),
                html.P(["Sem compra: ", html.Strong(formatos.numero(total["clientes_sem_compra"]))]),
                html.P(chip, className="positivo" if (variacao or 0) >= 0 else "negativo"),
            ]),
        ])
        cores_cob = ["#0e4d64" if m == mes else "#7fb3c2" for m in evolucao["mes"]]
        cores_rup = [cor_ruptura(v) for v in evolucao["perc_ruptura"]]
        titulo = f"Desempenho por vendedor · {formatos.mes_rotulo(mes)}"
        return (resumo, _barras(evolucao, "perc_cobertura", cores_cob), _barras(evolucao, "perc_ruptura", cores_rup),
                para_grade(do_mes), {"pinnedTopRowData": para_grade(pd.DataFrame([total]))}, titulo)

    @app.callback(
        Output("cm-r-download", "data"), Input("cm-r-exportar", "n_clicks"),
        State("cm-r-grade", "virtualRowData"), State("cm-r-grade", "columnDefs"), State("cm-r-grade", "dashGridOptions"),
        State("cm-revenda", "value"), State("cm-r-mes", "value"), State("cm-r-vendedor", "value"), prevent_initial_call=True,
    )
    def exportar_tela(_, linhas, colunas, opcoes_grade, revenda, mes, vendedor):
        total = (opcoes_grade or {}).get("pinnedTopRowData", [])
        tabela = exportar.tabela_da_grade(total + (linhas or []), colunas)
        planilha = exportar.planilha({"Ruptura": tabela}, [("Revenda", revenda), ("Mês", formatos.mes_rotulo(mes)),
                                                           ("Vendedor", exportar.texto_filtro(vendedor))])
        return dcc.send_bytes(planilha, f"ruptura_{revenda}_{mes}{'_' + str(vendedor) if vendedor else ''}.xlsx")
