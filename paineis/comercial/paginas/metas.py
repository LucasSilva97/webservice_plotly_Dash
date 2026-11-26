"""Página Metas: meta x realizado x tendência por vendedor, no mês escolhido."""
from datetime import date

import pandas as pd
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from paineis.comercial import dados
from paineis.comercial.paginas.diario import ESTILO_ATING, tom_atingimento
from paineis.comum import componentes as c
from paineis.comum import exportar, formatos, graficos
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
    return html.Div(className="vstack gap-3", children=[
        c.barra_filtros(
            c.filtro("Mês", dcc.Dropdown(id="cm-m-mes", options=[{"label": formatos.mes_rotulo(int(m)), "value": int(m)} for m in meses],
                                         value=atual, clearable=False)),
            dbc.Col(html.Span(id="cm-m-nota", className=c.NOTA), xs=12, lg=True),
        ),
        c.linha_cards("cm-m-cards"),
        c.secao(graficos.grafico("cm-m-grafico", 280), titulo="Meta x tendência por vendedor"),
        c.secao(
            c.barra_tabela("Metas do mês", c.botao("⬇ Exportar", "cm-m-exportar")),
            c.grade("cm-m-grade", COLUNAS, altura=300),
            c.nota("A linha fixa no topo é a meta própria da revenda, definida à parte (não é a soma dos vendedores). "
                   "Caixas e meta de caixas contam só os produtos do fabricante do programa."),
            dcc.Download(id="cm-m-download"),
        ),
    ])


def grafico_metas(linhas):
    """Meta contra tendência, lado a lado, por vendedor."""
    return graficos.opcao(
        grid={"left": 8, "right": 16, "top": 16, "bottom": 36, "containLabel": True},
        tooltip={**graficos.TOOLTIP_EIXO, "valueFormatter": "fn:moeda"},
        legend=graficos.LEGENDA,
        xAxis=graficos.eixo_categoria(linhas["vendedor"] if len(linhas) else []),
        yAxis=graficos.eixo_valor("moedaCurta"),
        series=[
            graficos.barras("meta", "Meta", graficos.valores(linhas["meta"]) if len(linhas) else [], graficos.CINZA),
            graficos.barras("tendencia", "Tendência", graficos.valores(linhas["tendencia"]) if len(linhas) else [], graficos.AZUL),
        ],
    )


def registrar(app):
    graficos.registrar(app, "cm-m-grafico")

    @app.callback(
        Output("cm-m-cards", "children"), Output("cm-m-grafico", "data"), Output("cm-m-grade", "rowData"),
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
        if 0 < dias["decorridos"] < dias["uteis"]:
            nota = f"Mês em andamento: {dias['decorridos']} de {dias['uteis']} dias úteis; tendência projetada."
        elif dias["decorridos"] == 0:
            nota = "Mês futuro: só a meta."
        else:
            nota = "Mês fechado: tendência = realizado."
        return cards, grafico_metas(linhas), para_grade(linhas), {"pinnedTopRowData": para_grade(pd.DataFrame([total]))}, nota

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
