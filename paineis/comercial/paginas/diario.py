"""Página Diário de Vendas: realizado do mês corrente, tendência e meta."""
from datetime import date

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from paineis.comercial import dados
from paineis.comum import componentes as c
from paineis.comum import exportar, formatos, graficos
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
    return html.Div(className="vstack gap-3", children=[
        c.barra_filtros(
            c.filtro("Vendedor", c.dropdown("cm-d-vendedor")),
            c.filtro("Canal", c.dropdown("cm-d-canal", options=[{"label": v, "value": k} for k, v in dados.CANAIS.items()])),
            c.filtro("Marca", c.dropdown("cm-d-marca", options=opcoes(marcas))),
            dbc.Col(html.Span(id="cm-d-periodo", className=c.NOTA), xs=12, lg=True),
        ),
        c.linha_cards("cm-d-cards"),
        dbc.Row(className="g-3", children=[
            dbc.Col(c.secao(graficos.grafico("cm-d-ritmo", 300), titulo="Ritmo do mês", className="h-100"), lg=6),
            dbc.Col(c.secao(graficos.grafico("cm-d-marcas", 300), titulo="Realizado por marca x ano anterior (até a mesma data)",
                            className="h-100"), lg=6),
        ]),
        c.secao(
            c.barra_tabela("Desempenho por vendedor", c.botao("⬇ Exportar", "cm-d-exportar")),
            c.grade("cm-d-grade", COLUNAS, altura=260),
            c.nota("A meta segue os filtros de vendedor e canal; ela não é aberta por marca. "
                   "Tendência = realizado / dias úteis decorridos x dias úteis do mês."),
            dcc.Download(id="cm-d-download"),
        ),
    ])


def grafico_ritmo(kpis, por_dia):
    """Realizado acumulado por dia útil contra a reta da meta, com a tendência até o fim do mês."""
    uteis = kpis["dias_uteis_mes"]
    dias = [0] + por_dia["dia_util"].tolist()
    acumulado = [0.0] + graficos.valores(por_dia["acumulado"])
    series = [
        {"id": "meta", "name": "Ritmo da meta", "type": "line", "symbol": "none", "z": 1,
         "lineStyle": {"type": "dashed", "color": graficos.CINZA_ESCURO, "width": 2}, "itemStyle": {"color": graficos.CINZA_ESCURO},
         "data": [[d, kpis["meta"] * d / uteis] for d in range(0, uteis + 1)]},
        {"id": "realizado", "name": "Realizado acumulado", "type": "line", "symbol": "circle", "symbolSize": 6, "showSymbol": False,
         "lineStyle": {"color": graficos.AZUL, "width": 3}, "itemStyle": {"color": graficos.AZUL}, "z": 3,
         "areaStyle": {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1, "colorStops": [
             {"offset": 0, "color": "rgba(14,77,100,0.22)"}, {"offset": 1, "color": "rgba(14,77,100,0.02)"}]}},
         "data": [list(p) for p in zip(dias, acumulado)]},
    ]
    if len(por_dia):
        ultimo = por_dia.iloc[-1]
        series.append({"id": "tendencia", "name": "Tendência", "type": "line", "symbol": "none", "z": 2,
                       "lineStyle": {"type": "dotted", "color": graficos.AMBAR, "width": 3}, "itemStyle": {"color": graficos.AMBAR},
                       "data": [[float(ultimo["dia_util"]), float(ultimo["acumulado"])], [uteis, float(kpis["tendencia"])]]})
    return graficos.opcao(
        grid={"left": 8, "right": 16, "top": 16, "bottom": 56, "containLabel": True},
        tooltip={**graficos.TOOLTIP_EIXO, "axisPointer": {"type": "line"}, "valueFormatter": "fn:moeda"},
        legend=graficos.LEGENDA,
        xAxis={"type": "value", "min": 0, "max": uteis, "minInterval": 1, "name": "dia útil do mês", "nameLocation": "middle",
               "nameGap": 26, "nameTextStyle": graficos.ROTULO_EIXO, "axisLabel": graficos.ROTULO_EIXO, "splitLine": {"show": False},
               "axisLine": {"lineStyle": {"color": graficos.BORDA}}},
        yAxis=graficos.eixo_valor("moedaCurta"),
        series=series,
    )


def grafico_marcas(por_marca):
    """Barras horizontais: mês atual contra o mesmo período do ano anterior, por marca."""
    return graficos.opcao(
        grid={"left": 8, "right": 16, "top": 8, "bottom": 36, "containLabel": True},
        tooltip={**graficos.TOOLTIP_EIXO, "valueFormatter": "fn:moeda"},
        legend=graficos.LEGENDA,
        xAxis=graficos.eixo_valor("moedaCurta"),
        yAxis=graficos.eixo_categoria(por_marca["marca"]),
        series=[
            graficos.barras("anterior", "Ano anterior", graficos.valores(por_marca["ano_anterior"]), graficos.CINZA, horizontal=True),
            graficos.barras("atual", "Mês atual", graficos.valores(por_marca["atual"]), graficos.AZUL, horizontal=True),
        ],
    )


def registrar(app):
    graficos.registrar(app, "cm-d-ritmo", "cm-d-marcas")

    @app.callback(Output("cm-d-vendedor", "options"), Input("cm-revenda", "value"))
    def vendedores(revenda):
        metas = ler_parquet("metas_mes")
        nomes = metas[(metas["revenda_id"] == revenda) & (metas["vendedor_id"] != 0)][["vendedor_id", "vendedor"]].drop_duplicates()
        return [{"label": v.vendedor, "value": v.vendedor_id} for v in nomes.sort_values("vendedor_id").itertuples()]

    @app.callback(
        Output("cm-d-cards", "children"), Output("cm-d-ritmo", "data"), Output("cm-d-marcas", "data"),
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
