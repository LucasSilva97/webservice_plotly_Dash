"""Página Carteira de clientes: base analítica com filtros cruzados (cada lista mostra só o
que existe nos outros filtros escolhidos)."""
from datetime import date

from dash import ALL, Input, Output, State, ctx, dcc, html

from paineis.comercial import dados
from paineis.comum import componentes as c
from paineis.comum import exportar, formatos
from paineis.comum.dados import para_grade

LIMITE_VENCIDO_CRITICO = 5000  # vencido acima disso fica em destaque (valor inventado)
ESTILO_VENCIDO = {"styleConditions": [
    {"condition": f"params.value >= {LIMITE_VENCIDO_CRITICO}", "style": {"backgroundColor": "#fde2e2", "color": "#c0392b", "fontWeight": "700"}},
    {"condition": "params.value > 0", "style": {"color": "#c0392b", "fontWeight": "600"}},
]}
ESTILO_MES = {"backgroundColor": "#f2f8f4"}


def colunas():
    meses = dados.rotulos_meses()
    return [
        c.coluna("cliente_id", "Cód.", largura=90, pinned="left"),
        c.coluna("fantasia", "Cliente", largura=220, pinned="left"),
        c.coluna("razao_social", "Razão social", largura=260),
        c.coluna("vendedor_id", "Vend.", largura=85),
        c.coluna("canal", "Canal", largura=120), c.coluna("classe", "Classe", largura=125),
        c.coluna("cidade", "Cidade", largura=130), c.coluna("bairro", "Bairro", largura=150),
        c.coluna("valor_vencido", "Vencido R$", "moeda", largura=125, cellStyle=ESTILO_VENCIDO),
        c.coluna("valor_aberto", "Em aberto R$", "moeda", largura=125),
        c.coluna("faixa_atraso", "Tempo de atraso", largura=135),
        c.coluna("vencimento_mais_antigo", "Venc. mais antigo", "data", largura=140),
        c.coluna("geladeira_vertical", "Geladeira", "inteiro", largura=100),
        c.coluna("freezer_horizontal", "Freezer", "inteiro", largura=95),
        c.coluna("carrinho_termico", "Carrinho", "inteiro", largura=95),
        c.coluna("equipamentos_total", "Equip.", "inteiro", largura=85),
        c.coluna("retorno_por_equipamento", "R$ / equip.", "moeda", largura=120),
        c.coluna("ultima_compra_mes", "Última compra", "mes", largura=120),
        *[c.coluna(f"fat_m{k}", meses[f"fat_m{k}"], "moeda", largura=115, cellStyle=ESTILO_MES) for k in range(4, -1, -1)],
        c.coluna("media_fat_3m", "Média 3 meses", "moeda", largura=130),
    ]


def layout():
    filtros = [c.filtro(rotulo, c.dropdown({"tipo": "cm-c-filtro", "campo": campo}))
               for campo, rotulo in dados.FILTROS_CARTEIRA.items()]
    return html.Div([
        html.Section(className="secao barra-filtros", children=[
            c.filtro("Situação", dcc.RadioItems(id="cm-c-situacao", options=["Ativo", "Inativo"], value="Ativo", className="radio-pilula")),
            c.filtro("Classe", dcc.RadioItems(id="cm-c-classe", options=["Todos", "Grandes Redes", "Regular"], value="Todos", className="radio-pilula")),
            *filtros,
            html.Button("Limpar filtros", id="cm-c-limpar", className="botao secundario"),
        ]),
        html.Div(id="cm-c-cards", className="cards"),
        html.Section(className="secao", children=[
            html.Div(className="barra-tabela", children=[
                html.H2("Carteira analítica de clientes"),
                html.Button("⬇ Exportar", id="cm-c-exportar", className="botao secundario"),
            ]),
            c.grade("cm-c-grade", colunas(), altura=560, dashGridOptions={"pagination": True, "paginationPageSize": 50}),
            html.P("Faturamento líquido dos 5 meses mais recentes (o último é o mês corrente, parcial). "
                   "Média 3 meses = meses fechados. Filtros cruzados: cada lista só mostra o que existe nos demais filtros.",
                   className="nota"),
            dcc.Download(id="cm-c-download"),
        ]),
    ])


def registrar(app):
    filtro_valores = Input({"tipo": "cm-c-filtro", "campo": ALL}, "value")

    @app.callback(
        Output("cm-c-cards", "children"), Output("cm-c-grade", "rowData"),
        Output({"tipo": "cm-c-filtro", "campo": ALL}, "options"),
        Input("cm-revenda", "value"), Input("cm-c-situacao", "value"), Input("cm-c-classe", "value"), filtro_valores,
    )
    def atualizar(revenda, situacao, classe, _):
        valores = {item["id"]["campo"]: item.get("value") for item in ctx.inputs_list[3]}
        df, opcoes = dados.carteira(revenda, situacao, classe, valores)
        cards = [
            c.card("Clientes", formatos.numero(len(df)), f"{situacao.lower()}s no recorte", "escuro"),
            c.card("Inadimplentes", formatos.numero((df["valor_vencido"] > 0).sum()), formatos.moeda_curta(df["valor_vencido"].sum()) + " vencidos", "vermelho"),
            c.card("Em aberto", formatos.moeda_curta(df["valor_aberto"].sum()), "títulos a vencer e vencidos", "neutro"),
            c.card("Sem compra no mês", formatos.numero((df["faixa_m0"] == "Sem compra").sum()), "ruptura da carteira no mês corrente", "ambar"),
            c.card("Equipamentos cedidos", formatos.numero(df["equipamentos_total"].sum()), f"média 3 meses {formatos.moeda_curta(df['media_fat_3m'].sum())}", "azul"),
        ]
        ordem = [item["id"]["campo"] for item in ctx.outputs_list[2]]
        return cards, para_grade(df), [opcoes[campo] for campo in ordem]

    @app.callback(
        Output({"tipo": "cm-c-filtro", "campo": ALL}, "value"), Output("cm-c-classe", "value"),
        Input("cm-c-limpar", "n_clicks"), State({"tipo": "cm-c-filtro", "campo": ALL}, "id"), prevent_initial_call=True,
    )
    def limpar(_, ids):
        return [None] * len(ids), "Todos"

    @app.callback(
        Output("cm-c-download", "data"), Input("cm-c-exportar", "n_clicks"),
        State("cm-c-grade", "virtualRowData"), State("cm-c-grade", "columnDefs"),
        State("cm-revenda", "value"), State("cm-c-situacao", "value"), State("cm-c-classe", "value"),
        State({"tipo": "cm-c-filtro", "campo": ALL}, "value"), State({"tipo": "cm-c-filtro", "campo": ALL}, "id"),
        prevent_initial_call=True,
    )
    def exportar_tela(_, linhas, colunas_grade, revenda, situacao, classe, valores, ids):
        filtros = [("Revenda", revenda), ("Situação", situacao), ("Classe", classe)] + [
            (dados.FILTROS_CARTEIRA[i["campo"]], exportar.texto_filtro(v)) for i, v in zip(ids, valores)]
        planilha = exportar.planilha({"Carteira de clientes": exportar.tabela_da_grade(linhas, colunas_grade)}, filtros)
        return dcc.send_bytes(planilha, f"carteira_clientes_{revenda}_{date.today():%Y-%m-%d}.xlsx")
