"""Página Diário de Vendas: realizado do mês corrente, tendência e meta."""
from datetime import date

import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

from paineis.comercial import dados
from paineis.comum import componentes as c
from paineis.comum import exportar, formatos
from paineis.comum.dados import ler_parquet, opcoes, para_grade

ESTILO_ATING = {"styleConditions": [
    {"condition": "params.value !== null && params.value < 95", "style": {"color": "#c0392b", "fontWeight": "700"}},
    {"condition": "params.value >= 95 && params.value < 100", "style": {"color": "#c98303", "fontWeight": "700"}},
    {"condition": "params.value >= 100", "style": {"color": "#2e8b57", "fontWeight": "700"}},
]}
COLUNAS = [
    c.coluna("vendedor", "Vendedor", largura=150, pinned="left"),
    c.coluna("realizado", "Realizado", "moeda", largura=140),
    c.coluna("tendencia", "Tendência", "moeda", largura=140),
    c.coluna("meta", "Meta", "moeda", largura=140),
    c.coluna("ating", "% ating. (tend.)", "pct", largura=140, cellStyle=ESTILO_ATING),
    c.coluna("caixas", "Caixas", "inteiro", largura=110),
    c.coluna("positivados", "Positivados", "inteiro", largura=120),
    c.coluna("meta_clientes", "Meta clientes", "inteiro", largura=125),
    c.coluna("ating_clientes", "% positivação", "pct", largura=130, cellStyle=ESTILO_ATING),
]


def tom_atingimento(valor):
    return "verde" if valor and valor >= 100 else "ambar" if valor and valor >= 95 else "vermelho"


def layout():
    marcas = ler_parquet("vendas_diarias")["marca"]
    return html.Div([
        html.Section(className="secao barra-filtros", children=[
            c.filtro("Vendedor", c.dropdown("cm-d-vendedor")),
            c.filtro("Canal", c.dropdown("cm-d-canal", options=[{"label": v, "value": k} for k, v in dados.CANAIS.items()])),
            c.filtro("Marca", c.dropdown("cm-d-marca", options=opcoes(marcas))),
            html.Span(id="cm-d-periodo", className="nota"),
        ]),
        html.Div(id="cm-d-cards", className="cards"),
        html.Div(className="graficos", children=[
            html.Section(className="secao", children=[html.H2("Ritmo do mês"), dcc.Graph(id="cm-d-ritmo", config={"displayModeBar": False})]),
            html.Section(className="secao", children=[html.H2("Realizado por marca x ano anterior (até a mesma data)"),
                                                      dcc.Graph(id="cm-d-marcas", config={"displayModeBar": False})]),
        ]),
        html.Section(className="secao", children=[
            html.Div(className="barra-tabela", children=[
                html.H2("Desempenho por vendedor"),
                html.Button("⬇ Exportar", id="cm-d-exportar", className="botao secundario"),
            ]),
            c.grade("cm-d-grade", COLUNAS, altura=260),
            html.P("A meta segue os filtros de vendedor e canal; ela não é aberta por marca. "
                   "Tendência = realizado / dias úteis decorridos x dias úteis do mês.", className="nota"),
            dcc.Download(id="cm-d-download"),
        ]),
    ])


def grafico_ritmo(kpis, por_dia):
    uteis = kpis["dias_uteis_mes"]
    figura = go.Figure()
    figura.add_scatter(x=list(range(0, uteis + 1)), y=[kpis["meta"] * d / uteis for d in range(0, uteis + 1)],
                       name="Ritmo da meta", line={"dash": "dash", "color": "#5d6d75"})
    figura.add_scatter(x=[0] + por_dia["dia_util"].tolist(), y=[0] + por_dia["acumulado"].tolist(),
                       name="Realizado acumulado", line={"color": "#0e4d64", "width": 3})
    if len(por_dia):
        ultimo = por_dia.iloc[-1]
        figura.add_scatter(x=[ultimo["dia_util"], uteis], y=[ultimo["acumulado"], kpis["tendencia"]],
                           name="Tendência", line={"dash": "dot", "color": "#f2a93b", "width": 3})
    figura.update_layout(height=300, margin={"l": 10, "r": 10, "t": 10, "b": 10}, separators=",.",
                         xaxis_title="dia útil do mês", yaxis_tickprefix="R$ ", legend={"orientation": "h", "y": -0.25},
                         plot_bgcolor="#fff")
    return figura


def grafico_marcas(por_marca):
    figura = go.Figure()
    figura.add_bar(y=por_marca["marca"], x=por_marca["ano_anterior"], orientation="h", name="Ano anterior", marker_color="#c9d3d8")
    figura.add_bar(y=por_marca["marca"], x=por_marca["atual"], orientation="h", name="Mês atual", marker_color="#0e4d64")
    figura.update_layout(height=300, margin={"l": 10, "r": 10, "t": 10, "b": 10}, separators=",.", barmode="group",
                         xaxis_tickprefix="R$ ", legend={"orientation": "h", "y": -0.2}, plot_bgcolor="#fff")
    return figura


def registrar(app):
    @app.callback(Output("cm-d-vendedor", "options"), Input("cm-revenda", "value"))
    def vendedores(revenda):
        metas = ler_parquet("metas_mes")
        nomes = metas[(metas["revenda_id"] == revenda) & (metas["vendedor_id"] != 0)][["vendedor_id", "vendedor"]].drop_duplicates()
        return [{"label": v.vendedor, "value": v.vendedor_id} for v in nomes.sort_values("vendedor_id").itertuples()]

    @app.callback(
        Output("cm-d-cards", "children"), Output("cm-d-ritmo", "figure"), Output("cm-d-marcas", "figure"),
        Output("cm-d-grade", "rowData"), Output("cm-d-periodo", "children"),
        Input("cm-revenda", "value"), Input("cm-d-vendedor", "value"), Input("cm-d-canal", "value"), Input("cm-d-marca", "value"),
    )
    def atualizar(revenda, vendedores, canais, marcas):
        k, por_dia, por_marca, tabela = dados.diario(revenda, vendedores, canais, marcas)
        cards = [
            c.card("Realizado no mês", formatos.moeda_curta(k["realizado"]),
                   f"{formatos.pct(k['var_ano_anterior'])} vs ano anterior até a data", "escuro"),
            c.card("Tendência", formatos.moeda_curta(k["tendencia"]),
                   f"{formatos.pct(k['var_mes_anterior'])} vs mês anterior fechado", "azul"),
            c.card("Meta", formatos.moeda_curta(k["meta"]), "meta do recorte (vendedor/canal)", "neutro"),
            c.card("Atingimento (tendência)", formatos.pct(k["ating_tendencia"]), "verde a partir de 100%",
                   tom_atingimento(k["ating_tendencia"])),
            c.card("Caixas", formatos.numero(k["caixas"]), f"mix de {k['mix']} produtos", "neutro"),
            c.card("Positivação", formatos.numero(k["positivados"]),
                   f"{formatos.pct(k['ating_clientes'])} da meta de {formatos.numero(k['meta_clientes'])} clientes",
                   tom_atingimento(k["ating_clientes"])),
        ]
        periodo = (f"{formatos.mes_rotulo(k['mes'])} · {k['dias_uteis_decorridos']} de {k['dias_uteis_mes']} dias úteis "
                   f"até {formatos.data(k['data_referencia'])}")
        return cards, grafico_ritmo(k, por_dia), grafico_marcas(por_marca), para_grade(tabela), periodo

    @app.callback(
        Output("cm-d-download", "data"), Input("cm-d-exportar", "n_clicks"),
        State("cm-d-grade", "virtualRowData"), State("cm-d-grade", "columnDefs"),
        State("cm-revenda", "value"), State("cm-d-vendedor", "value"), State("cm-d-canal", "value"), State("cm-d-marca", "value"),
        prevent_initial_call=True,
    )
    def exportar_tela(_, linhas, colunas, revenda, vendedores, canais, marcas):
        planilha = exportar.planilha({"Diário de vendas": exportar.tabela_da_grade(linhas, colunas)}, [
            ("Revenda", revenda), ("Vendedor", exportar.texto_filtro(vendedores)),
            ("Canal", exportar.texto_filtro(canais)), ("Marca", exportar.texto_filtro(marcas))])
        return dcc.send_bytes(planilha, f"diario_vendas_{revenda}_{date.today():%Y-%m-%d}.xlsx")
