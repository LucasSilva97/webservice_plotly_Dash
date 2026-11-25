"""Página Metas: meta x realizado x tendência por vendedor, no mês escolhido."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

from paineis.comercial import dados
from paineis.comercial.paginas.diario import ESTILO_ATING, tom_atingimento
from paineis.comum import componentes as c
from paineis.comum import exportar, formatos
from paineis.comum.dados import ler_parquet, para_grade

COLUNAS = [
    c.coluna("vendedor", "Vendedor", largura=190, pinned="left"),
    c.coluna("meta", "Meta R$", "moeda", largura=135),
    c.coluna("realizado", "Realizado R$", "moeda", largura=135),
    c.coluna("tendencia", "Tendência R$", "moeda", largura=135),
    c.coluna("ating", "% ating.", "pct", largura=105, cellStyle=ESTILO_ATING),
    c.coluna("meta_caixas", "Meta cx fabricante", "inteiro", largura=150),
    c.coluna("caixas", "Cx fabricante", "inteiro", largura=125),
    c.coluna("ating_caixas", "% cx", "pct", largura=95, cellStyle=ESTILO_ATING),
    c.coluna("meta_clientes", "Meta clientes", "inteiro", largura=120),
    c.coluna("positivados", "Positivados", "inteiro", largura=115),
    c.coluna("ating_clientes", "% clientes", "pct", largura=110, cellStyle=ESTILO_ATING),
]


def layout():
    meses = sorted(ler_parquet("metas_mes")["mes"].unique(), reverse=True)
    atual = int(dados.periodo_atual()["mes"])
    return html.Div([
        html.Section(className="secao barra-filtros", children=[
            c.filtro("Mês", dcc.Dropdown(id="cm-m-mes", options=[{"label": formatos.mes_rotulo(int(m)), "value": int(m)} for m in meses],
                                         value=atual, clearable=False, className="dropdown")),
            html.Span(id="cm-m-nota", className="nota"),
        ]),
        html.Div(id="cm-m-cards", className="cards"),
        html.Section(className="secao", children=[html.H2("Meta x tendência por vendedor"),
                                                  dcc.Graph(id="cm-m-grafico", config={"displayModeBar": False})]),
        html.Section(className="secao", children=[
            html.Div(className="barra-tabela", children=[
                html.H2("Metas do mês"),
                html.Button("⬇ Exportar", id="cm-m-exportar", className="botao secundario"),
            ]),
            c.grade("cm-m-grade", COLUNAS, altura=300),
            html.P("A linha fixa no topo é a meta própria da revenda, definida à parte (não é a soma dos vendedores). "
                   "Caixas e meta de caixas contam só os produtos do fabricante do programa.", className="nota"),
            dcc.Download(id="cm-m-download"),
        ]),
    ])


def registrar(app):
    @app.callback(
        Output("cm-m-cards", "children"), Output("cm-m-grafico", "figure"), Output("cm-m-grade", "rowData"),
        Output("cm-m-grade", "dashGridOptions"), Output("cm-m-nota", "children"),
        Input("cm-revenda", "value"), Input("cm-m-mes", "value"),
    )
    def atualizar(revenda, mes):
        linhas, total, dias = dados.metas_do_mes(revenda, mes)
        cards = [
            c.card("Meta da revenda", formatos.moeda_curta(total["meta"]), "meta própria (vendedor 0)", "escuro"),
            c.card("Tendência", formatos.moeda_curta(total["tendencia"]), f"realizado {formatos.moeda_curta(total['realizado'])}", "azul"),
            c.card("Atingimento", formatos.pct(total["ating"]), "tendência / meta", tom_atingimento(total["ating"])),
            c.card("Caixas do fabricante", formatos.numero(total["caixas"]),
                   f"{formatos.pct(total['ating_caixas'])} de {formatos.numero(total['meta_caixas'])}", tom_atingimento(total["ating_caixas"])),
            c.card("Clientes positivados", formatos.numero(total["positivados"]),
                   f"{formatos.pct(total['ating_clientes'])} de {formatos.numero(total['meta_clientes'])}", tom_atingimento(total["ating_clientes"])),
        ]
        figura = go.Figure()
        if len(linhas):
            figura.add_bar(x=linhas["vendedor"], y=linhas["meta"], name="Meta", marker_color="#c9d3d8")
            figura.add_bar(x=linhas["vendedor"], y=linhas["tendencia"], name="Tendência", marker_color="#0e4d64")
        figura.update_layout(height=280, barmode="group", margin={"l": 10, "r": 10, "t": 10, "b": 10}, separators=",.",
                             yaxis_tickprefix="R$ ", legend={"orientation": "h", "y": -0.2}, plot_bgcolor="#fff")
        if 0 < dias["decorridos"] < dias["uteis"]:
            nota = f"Mês em andamento: {dias['decorridos']} de {dias['uteis']} dias úteis; tendência projetada."
        elif dias["decorridos"] == 0:
            nota = "Mês futuro: só a meta."
        else:
            nota = "Mês fechado: tendência = realizado."
        return cards, figura, para_grade(linhas), {"pinnedTopRowData": para_grade(pd.DataFrame([total]))}, nota

    @app.callback(
        Output("cm-m-download", "data"), Input("cm-m-exportar", "n_clicks"),
        State("cm-m-grade", "virtualRowData"), State("cm-m-grade", "columnDefs"), State("cm-m-grade", "dashGridOptions"),
        State("cm-revenda", "value"), State("cm-m-mes", "value"), prevent_initial_call=True,
    )
    def exportar_tela(_, linhas, colunas, opcoes_grade, revenda, mes):
        total = (opcoes_grade or {}).get("pinnedTopRowData", [])
        tabela = exportar.tabela_da_grade(total + (linhas or []), colunas)
        planilha = exportar.planilha({"Metas": tabela}, [("Revenda", revenda), ("Mês", formatos.mes_rotulo(mes))])
        return dcc.send_bytes(planilha, f"metas_{revenda}_{mes}_{date.today():%Y-%m-%d}.xlsx")
