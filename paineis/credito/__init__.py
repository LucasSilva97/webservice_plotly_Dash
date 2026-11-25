"""Painel Crédito e Prazo (/credito/): quatro abas declaradas em paginas.py, servidas por um
único conjunto de layout e callbacks."""
from datetime import date

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate

from paineis.comum import componentes as c
from paineis.comum import exportar, formatos
from paineis.comum.dados import RAIZ, data_geracao, data_referencia, ler_parquet, para_grade
from paineis.credito import dados, solicitacao
from paineis.credito.paginas import PAGINAS

PREFIXO = "/credito/"
ESCADA = [1500, 3000, 6000, 12000, 25000, 50000, 80000, 120000, 180000]  # a mesma var escada_limite do dbt
COLUNAS_PEDIDOS = [
    c.coluna("pedido_id", "Pedido", largura=95), c.coluna("data_emissao", "Emissão", "data", largura=110),
    c.coluna("valor_total", "Valor", "moeda", largura=120), c.coluna("prazo", "Prazo", largura=95),
    c.coluna("data_vencimento", "Vencimento", "data", largura=115), c.coluna("data_pagamento", "Pagamento", "data", largura=115),
    c.coluna("dias_atraso", "Dias de atraso", "inteiro", largura=120,
             cellStyle={"styleConditions": [{"condition": "params.value > 0", "style": {"color": "#c0392b", "fontWeight": "700"}}]}),
    c.coluna("situacao", "Situação", largura=110),
]


def pagina_da_url(caminho):
    slug = (caminho or "").removeprefix(PREFIXO).strip("/")
    return PAGINAS.get(slug)


def layout_pagina(pagina):
    seletor_opcoes = dados.opcoes_seletor(pagina) if pagina.seletor else []
    return html.Div([
        html.Section(className="secao barra-filtros", children=[
            html.Div(c.filtro("Data de implantação", dcc.Dropdown(
                id="cr-seletor", options=seletor_opcoes, value=seletor_opcoes[0]["value"] if seletor_opcoes else None,
                clearable=False, className="dropdown")), style={} if pagina.seletor else {"display": "none"}),
            c.filtro("Cliente (código ou nome)", c.dropdown("cr-cliente")),
            *[c.filtro(rotulo, c.dropdown({"tipo": "cr-filtro", "campo": campo})) for campo, rotulo in pagina.filtros.items()],
        ]),
        html.Div(id="cr-cards", className="cards"),
        html.Section(className="secao", children=[
            html.Div(className="barra-tabela", children=[
                html.Div([html.H2(pagina.titulo), html.Span(id="cr-contagem", className="nota")]),
                html.Button("⬇ Exportar Excel", id="cr-exportar", className="botao secundario"),
            ]),
            # Junto do botão: se o Download ficasse no layout raiz, o Dash dispararia a exportação
            # toda vez que a aba é montada (prevent_initial_call não vale nesse caso).
            dcc.Download(id="cr-download"),
            c.grade("cr-grade", pagina.colunas, altura=480, getRowId=f"params.data.{pagina.chave}",
                    dashGridOptions={"pagination": True, "paginationPageSize": 25,
                                     "rowSelection": {"mode": "singleRow", "checkboxes": False, "enableClickSelection": True}}),
            html.P("Clique em uma linha para ver os pedidos do cliente nos últimos 90 dias." if pagina.detalhe_cliente else "",
                   className="nota"),
        ]),
        # Detalhe do cliente: nasce escondido a cada aba e aparece ao selecionar uma linha.
        html.Section(id="cr-detalhe", className="secao", style={"display": "none"}, children=[
            html.Div(className="barra-tabela", children=[
                html.Div([html.H2(id="cr-detalhe-titulo"), html.Span(id="cr-detalhe-resumo", className="nota")]),
                html.Button("Solicitar alteração de limite/prazo", id="cr-abrir-solicitacao", className="botao",
                            style={} if pagina.slug == "" else {"display": "none"}),
            ]),
            c.grade("cr-grade-pedidos", COLUNAS_PEDIDOS, altura=260),
        ]),
    ])


def montar_layout():
    nomes = ler_parquet("credito_clientes")[["revenda_id", "revenda"]].drop_duplicates().sort_values("revenda_id")
    proxima = dados.proxima_implantacao()
    faltam = f" · próxima implantação de limite e prazo em {formatos.data(proxima)}" if proxima else ""
    return html.Div([
        dcc.Location(id="cr-url"),
        c.cabecalho("Crédito e Prazo", "Consulta de limite e prazo, cobrança, solicitações e histórico" + faltam, PREFIXO),
        html.Main(className="conteudo", children=[
            html.Div(className="secao-cabecalho", children=[
                html.Nav(id="cr-abas", className="abas"),
                html.Div(style={"minWidth": "260px"}, children=c.filtro("Revenda", dcc.Dropdown(
                    id="cr-revenda", options=[{"label": f"{r.revenda_id} · {r.revenda}", "value": r.revenda_id} for r in nomes.itertuples()],
                    value=20, clearable=False, className="dropdown"))),
            ]),
            html.Div(id="cr-pagina"),
            c.rodape_dados(data_geracao("credito_clientes"), data_referencia()),
        ]),
        c.modal("cr-sol", "Solicitar alteração", [
            html.P(id="cr-sol-cliente", className="nota"),
            html.Div(className="formulario", children=[
                c.filtro("Novo limite", dcc.Dropdown(id="cr-sol-limite", options=[{"label": formatos.moeda(v, 0), "value": v} for v in ESCADA],
                                                     placeholder="manter", className="dropdown")),
                c.filtro("Novo prazo", dcc.Dropdown(id="cr-sol-prazo", options=[{"label": "À vista" if d == 0 else f"{d} dias", "value": d}
                                                                                for d in solicitacao.PRAZOS_VALIDOS],
                                                    placeholder="manter", className="dropdown")),
                c.filtro("Solicitante", dcc.Input(id="cr-sol-solicitante", placeholder="ex.: V201", type="text")),
                c.filtro("Observação", dcc.Textarea(id="cr-sol-observacao", style={"minHeight": "60px"})),
            ]),
            html.Div(id="cr-sol-aviso"),
            html.Div(html.Button("Registrar solicitação", id="cr-sol-enviar", className="botao")),
            html.P("Grava só no ERP local da demonstração (data/fontes/erp.sqlite). A solicitação aparece na aba "
                   "Solicitações depois de rodar o ELT com --manter-fontes.", className="nota"),
        ], largura="720px"),
        dcc.Store(id="cr-cliente-selecionado"),
    ])


def criar_app(servidor):
    app = Dash(__name__, server=servidor, url_base_pathname=PREFIXO,
               assets_folder=str(RAIZ / "paineis" / "assets"), title="Crédito e Prazo · Andorinha",
               suppress_callback_exceptions=True, update_title=None)
    app.layout = montar_layout

    @app.callback(Output("cr-pagina", "children"), Output("cr-abas", "children"), Input("cr-url", "pathname"))
    def rotear(caminho):
        pagina = pagina_da_url(caminho)
        abas = [dcc.Link(p.titulo, href=f"{PREFIXO}{p.slug}", className="ativa" if p is pagina else "") for p in PAGINAS.values()]
        if pagina is None:
            return html.Div(className="secao", children=[html.H2("Página não encontrada"),
                                                         dcc.Link("Voltar para Limite e prazo", href=PREFIXO)]), abas
        return layout_pagina(pagina), abas

    # A URL é State: numa troca de aba quem dispara é a montagem dos componentes da aba nova. Como
    # Input, o callback rodava antes disso, com a URL nova e os filtros da aba antiga (KeyError).
    @app.callback(
        Output("cr-cards", "children"), Output("cr-grade", "rowData"), Output("cr-contagem", "children"),
        Output("cr-cliente", "options"), Output({"tipo": "cr-filtro", "campo": ALL}, "options"),
        Input("cr-revenda", "value"), Input("cr-seletor", "value"),
        Input("cr-cliente", "value"), Input({"tipo": "cr-filtro", "campo": ALL}, "value"),
        State("cr-url", "pathname"),
    )
    def atualizar(revenda, seletor, clientes, _, caminho):
        pagina = pagina_da_url(caminho)
        valores = {item["id"]["campo"]: item.get("value") for item in ctx.inputs_list[3]}
        if pagina is None or set(valores) != set(pagina.filtros):
            raise PreventUpdate  # filtros de outra aba ainda na tela (troca em andamento)
        base = dados.carregar(pagina, revenda, seletor)
        df = dados.aplicar(base, pagina, clientes, valores)
        opcoes = [dados.opcoes_filtro(base, item["id"]["campo"]) for item in ctx.outputs_list[4]]
        return pagina.cards(df), para_grade(df), f"{formatos.numero(len(df))} linhas", dados.opcoes_cliente(base), opcoes

    @app.callback(
        Output("cr-detalhe", "style"), Output("cr-detalhe-titulo", "children"), Output("cr-detalhe-resumo", "children"),
        Output("cr-grade-pedidos", "rowData"), Output("cr-cliente-selecionado", "data"),
        Input("cr-grade", "selectedRows"), State("cr-url", "pathname"), prevent_initial_call=True,
    )
    def detalhe(selecionadas, caminho):
        pagina = pagina_da_url(caminho)
        if not selecionadas or pagina is None or not pagina.detalhe_cliente:
            return {"display": "none"}, no_update, no_update, [], None
        linha = selecionadas[0]
        pedidos, resumo = dados.pedidos_do_cliente(linha["cliente_id"])
        nome = linha.get("fantasia") or linha.get("razao_social")
        texto = (f"{resumo['pedidos']} pedidos nos últimos 90 dias · {formatos.moeda(resumo['valor'])} faturados · "
                 f"atraso médio dos pagos {formatos.numero(resumo['media_atraso'], 1)} dias · {resumo['vencidos']} vencidos")
        cliente = {"cliente_id": linha["cliente_id"], "revenda_id": linha["revenda_id"], "nome": nome,
                   "limite_atual": linha.get("limite_atual"), "prazo_atual": linha.get("prazo_atual")}
        return {}, f"Pedidos de {linha['cliente_id']} – {nome}", texto, para_grade(pedidos), cliente

    @app.callback(
        Output("cr-sol-fundo", "className"), Output("cr-sol-cliente", "children"), Output("cr-sol-aviso", "children"),
        Input("cr-abrir-solicitacao", "n_clicks"), Input("cr-sol-fechar", "n_clicks"), Input("cr-sol-enviar", "n_clicks"),
        State("cr-cliente-selecionado", "data"), State("cr-sol-limite", "value"), State("cr-sol-prazo", "value"),
        State("cr-sol-solicitante", "value"), State("cr-sol-observacao", "value"), prevent_initial_call=True,
    )
    def solicitar(abrir, _, __, cliente, limite, prazo, solicitante, observacao):
        if ctx.triggered_id == "cr-abrir-solicitacao" and not abrir:
            raise PreventUpdate  # botão recém-montado pela troca de aba, ninguém clicou
        if ctx.triggered_id == "cr-sol-fechar" or not cliente:
            return "modal-fundo oculto", no_update, ""
        descricao = (f"{cliente['cliente_id']} – {cliente['nome']} · limite atual {formatos.moeda(cliente.get('limite_atual'))} "
                     f"· prazo atual {cliente.get('prazo_atual') or '—'}")
        if ctx.triggered_id == "cr-abrir-solicitacao":
            return "modal-fundo", descricao, ""
        try:
            numero = solicitacao.registrar(cliente["revenda_id"], cliente["cliente_id"], cliente.get("limite_atual"),
                                           limite, prazo, solicitante, observacao)
        except ValueError as erro:
            return no_update, no_update, html.Div(str(erro), className="aviso erro")
        return no_update, no_update, html.Div(f"Solicitação nº {numero} registrada no ERP local, em análise.", className="aviso")

    @app.callback(
        Output("cr-download", "data"), Input("cr-exportar", "n_clicks"),
        State("cr-grade", "virtualRowData"), State("cr-grade", "columnDefs"), State("cr-url", "pathname"),
        State("cr-revenda", "value"), State("cr-seletor", "value"), State("cr-cliente", "value"),
        State({"tipo": "cr-filtro", "campo": ALL}, "value"), State({"tipo": "cr-filtro", "campo": ALL}, "id"),
        prevent_initial_call=True,
    )
    def exportar_tela(cliques, linhas, colunas, caminho, revenda, seletor, clientes, valores, ids):
        pagina = pagina_da_url(caminho)
        if not cliques or pagina is None:
            raise PreventUpdate
        filtros = [("Painel", "Crédito e Prazo"), ("Página", pagina.titulo), ("Revenda", revenda),
                   ("Cliente", exportar.texto_filtro(clientes))]
        if pagina.seletor:
            filtros.append(("Data de implantação", seletor))
        filtros += [(pagina.filtros[i["campo"]], exportar.texto_filtro(v)) for i, v in zip(ids, valores)]
        planilha = exportar.planilha({pagina.titulo: exportar.tabela_da_grade(linhas, colunas)}, filtros)
        return dcc.send_bytes(planilha, f"credito_{pagina.slug or 'inicio'}_{revenda}_{date.today():%Y%m%d}.xlsx")

    return app
