"""Callbacks do painel de Estoque e Reposição. Cada callback relê o Parquet: a tela pega
sozinha a publicação nova, e não há DataFrame guardado no navegador."""
from datetime import date

from dash import Input, Output, State, ctx, dcc, html, no_update

from paineis.comum import componentes as c
from paineis.comum import exportar, formatos, graficos
from paineis.comum.dados import ler_parquet, para_grade
from paineis.estoque import dados

FILTROS = [Input("ep-revenda", "value"), Input("ep-periodo", "value"), Input("ep-base", "value"),
           Input("ep-marca", "value"), Input("ep-categoria", "value"), Input("ep-produto", "value"),
           Input("ep-acao", "value")]
ESTADO_FILTROS = [State(i.component_id, i.component_property) for i in FILTROS]
GAUGES = ("ep-gauge-sellin", "ep-gauge-marca", "ep-gauge-geral")


def montar_cards(i):
    return [
        c.card("Puxada", formatos.moeda_curta(i["puxada_rs"]), f"{formatos.pct(i['puxada_pct'])} do estoque · abaixo do mínimo", "azul"),
        c.card("Reduzir", formatos.moeda_curta(i["reduzir_rs"]), f"{formatos.pct(i['reduzir_pct'])} do estoque · acima do máximo", "vermelho"),
        c.card("Estoque", formatos.moeda_curta(i["estoque_rs"]), f"{formatos.numero(i['estoque_hl'], 1)} HL", "escuro"),
        c.card("Produtos em ruptura", formatos.numero(i["produtos_ruptura"]), "sem estoque e com venda no período",
               "vermelho" if i["produtos_ruptura"] else "verde"),
    ]


def descrever_filtros(revenda, periodo, base, marcas, categorias, produtos, acao):
    return [("Revenda", revenda), ("Período", dados.PERIODOS[periodo]), ("Base do estoque", dados.BASES[base]),
            ("Marca", exportar.texto_filtro(marcas)), ("Categoria", exportar.texto_filtro(categorias)),
            ("Produto", exportar.texto_filtro(produtos)), ("Ação", dados.ACOES[acao])]


def registrar(app):
    graficos.registrar(app, *GAUGES)

    @app.callback(
        Output("ep-cards", "children"), Output("ep-gauge-sellin", "data"), Output("ep-gauge-marca", "data"),
        Output("ep-gauge-geral", "data"), Output("ep-grade", "rowData"), Output("ep-contagem", "children"),
        *FILTROS,
    )
    def atualizar(revenda, periodo, base, marcas, categorias, produtos, acao):
        df = dados.filtrar(dados.carregar(), revenda, periodo, base, marcas, categorias, produtos, acao)
        i = dados.indicadores(df, ler_parquet("sellin_sellout_mes"))
        contagem = df["data_contagem"].dropna()
        texto = f"Última contagem física: {formatos.data(contagem.max())}" if len(contagem) else "Sem contagem física"
        texto += f" · {len(df)} produtos"
        return (
            montar_cards(i),
            graficos.gauge(i["sellin_pct"], 200, (90, 110), "pct"),
            graficos.gauge(i["dde_marca"], 30, dados.FAIXA_DDE, divisoes=3),
            graficos.gauge(i["dde_geral"], 30, dados.FAIXA_DDE, divisoes=3),
            para_grade(df),
            texto,
        )

    @app.callback(
        Output("ep-marca", "value"), Output("ep-categoria", "value"), Output("ep-produto", "value"), Output("ep-acao", "value"),
        Input("ep-limpar", "n_clicks"), prevent_initial_call=True,
    )
    def limpar(_):
        return None, None, None, "TODOS"

    @app.callback(
        Output("ep-download", "data"),
        Input("ep-exportar", "n_clicks"),
        State("ep-grade", "virtualRowData"), State("ep-grade", "columnDefs"), *ESTADO_FILTROS,
        prevent_initial_call=True,
    )
    def exportar_tela(_, linhas, colunas, *filtros):
        planilha = exportar.planilha({"Estoque e Reposição": exportar.tabela_da_grade(linhas, colunas)},
                                     descrever_filtros(*filtros))
        return dcc.send_bytes(planilha, f"estoque_reposicao_{filtros[0]}_{date.today():%Y-%m-%d}.xlsx")

    @app.callback(
        Output("ep-detalhe-fundo", "className"), Output("ep-detalhe-titulo", "children"),
        Output("ep-grade-notas", "rowData"), Output("ep-grade-recebidas", "rowData"),
        Input("ep-grade", "cellClicked"), Input("ep-detalhe-fechar", "n_clicks"),
        State("ep-revenda", "value"), prevent_initial_call=True,
    )
    def detalhe(clique, _, revenda):
        if ctx.triggered_id == "ep-detalhe-fechar":
            return "modal-fundo oculto", no_update, no_update, no_update
        if not clique or clique.get("colId") not in ("qtd_transito", "transf_apos_compra") or not clique.get("value"):
            return no_update, no_update, no_update, no_update
        produto = int(clique["rowId"])
        notas, recebidas = dados.detalhe_produto(revenda, produto)
        nome = notas["produto"].iloc[0] if len(notas) else f"produto {produto}"
        return "modal-fundo", f"{produto} – {nome}", para_grade(notas), para_grade(recebidas)

    @app.callback(
        Output("ep-snap-fundo", "className"), Output("ep-snap-data", "options"), Output("ep-snap-data", "value"),
        Input("ep-abrir-snapshots", "n_clicks"), Input("ep-snap-fechar", "n_clicks"), prevent_initial_call=True,
    )
    def abrir_snapshots(_, __):
        if ctx.triggered_id == "ep-snap-fechar":
            return "modal-fundo oculto", no_update, no_update
        datas = dados.datas_snapshot()
        opcoes = [{"label": formatos.data(date.fromisoformat(d)), "value": d} for d in datas]
        return "modal-fundo", opcoes, (datas[0] if datas else None)

    @app.callback(
        Output("ep-snap-resumo", "children"), Output("ep-snap-grade", "rowData"), Output("ep-snap-filtros", "children"),
        Input("ep-snap-data", "value"), *ESTADO_FILTROS, prevent_initial_call=True,
    )
    def montar_snapshot(data_snapshot, *filtros):
        if not data_snapshot:
            return html.P("Nenhum snapshot gravado ainda.", className="nota"), [], ""
        df = dados.filtrar(dados.carregar_snapshot(data_snapshot), *filtros)
        texto = "Filtros da tela: " + "; ".join(f"{k}: {v}" for k, v in descrever_filtros(*filtros))
        return montar_cards(dados.indicadores(df)), para_grade(df), texto

    @app.callback(
        Output("ep-snap-download", "data"),
        Input("ep-snap-exportar", "n_clicks"),
        State("ep-snap-grade", "virtualRowData"), State("ep-snap-grade", "columnDefs"), State("ep-snap-data", "value"),
        *ESTADO_FILTROS, prevent_initial_call=True,
    )
    def exportar_snapshot(_, linhas, colunas, data_snapshot, *filtros):
        planilha = exportar.planilha({"Snapshot": exportar.tabela_da_grade(linhas, colunas)},
                                     [("Snapshot de", data_snapshot)] + descrever_filtros(*filtros))
        return dcc.send_bytes(planilha, f"estoque_reposicao_{filtros[0]}_snapshot_{data_snapshot}.xlsx")
