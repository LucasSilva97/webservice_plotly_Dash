"""Layout do painel de Estoque e Reposição."""
import dash_bootstrap_components as dbc
from dash import dcc, html

from paineis.comum import componentes as c
from paineis.comum import graficos
from paineis.comum.dados import data_geracao, data_referencia, opcoes
from paineis.estoque import dados

ESTILO_ACAO = {"styleConditions": [
    {"condition": "params.value < 0", "style": {"color": "#c0392b", "fontWeight": "700"}},
    {"condition": "params.value > 0", "style": {"color": "#1f6fb2", "fontWeight": "700"}},
]}
ESTILO_DDE = {"styleConditions": [
    {"condition": f"params.value !== null && params.value < {dados.FAIXA_DDE[0]}", "style": {"color": "#c0392b", "fontWeight": "600"}},
    {"condition": f"params.value > {dados.FAIXA_DDE[1]}", "style": {"color": "#c98303", "fontWeight": "600"}},
]}
ESTILO_LINK = {"styleConditions": [{"condition": "params.value > 0", "style": {"color": "#1f6fb2", "textDecoration": "underline", "cursor": "pointer", "fontWeight": "600"}}]}
ESTILO_COMPRA = {"styleConditions": [{"condition": "params.data.compra_antiga", "style": {"backgroundColor": "#fde2e2", "color": "#c0392b", "fontWeight": "600"}}]}

COLUNAS = [
    c.coluna("produto_id", "Código", largura=90, pinned="left"),
    c.coluna("produto", "Produto", largura=330, pinned="left"),
    c.coluna("marca", "Marca", largura=130),
    c.coluna("custo_caixa", "Custo cx", "moeda", largura=110),
    c.coluna("saldo_caixas", "Estoque (cx)", "inteiro", largura=115),
    c.coluna("hl_estoque", "Estoque (HL)", "dec1", largura=115),
    c.coluna("estoque_minimo", "Mínimo", "inteiro", largura=95),
    c.coluna("estoque_maximo", "Máximo", "inteiro", largura=95),
    c.coluna("reduzir_puxar", "Puxar / reduzir", "inteiro", largura=130, cellStyle=ESTILO_ACAO, headerClass="cab-acao"),
    c.coluna("analise_rs", "Análise R$", "moeda", largura=130, cellStyle=ESTILO_ACAO, headerClass="cab-acao"),
    c.coluna("puxada_maxima", "Puxada máxima", "inteiro", largura=125, headerClass="cab-acao"),
    c.coluna("estoque_valorizado", "Estoque R$", "moeda", largura=130),
    c.coluna("qtd_vendida", "Vendido (cx)", "inteiro", largura=115),
    c.coluna("media_venda_dia", "Média/dia útil", "dec2", largura=125),
    c.coluna("dde", "Dias de estoque", "dec1", largura=125, cellStyle=ESTILO_DDE, headerClass="cab-dias"),
    c.coluna("qtd_transito", "Em trânsito", "inteiro", largura=115, cellStyle=ESTILO_LINK, headerClass="cab-transito"),
    c.coluna("dde_com_transito", "Dias c/ trânsito", "dec1", largura=125, cellStyle=ESTILO_DDE, headerClass="cab-transito"),
    c.coluna("transf_apos_compra", "Transf. após compra", "inteiro", largura=140, cellStyle=ESTILO_LINK),
    c.coluna("ultima_compra", "Última compra", "data", largura=125, cellStyle=ESTILO_COMPRA),
]

COLUNAS_NOTAS = [
    c.coluna("tipo", "Tipo", largura=120), c.coluna("documento", "Documento", largura=110),
    c.coluna("origem", "Origem", largura=170), c.coluna("data_emissao", "Emissão", "data", largura=110),
    c.coluna("qtd_caixas", "Caixas", "inteiro", largura=90), c.coluna("dias_em_transito", "Dias em trânsito", "inteiro", largura=130),
]
COLUNAS_RECEBIDAS = [
    c.coluna("nf_transferencia", "Nota", largura=110), c.coluna("origem", "Origem", largura=170),
    c.coluna("data_entrada", "Entrada", "data", largura=110), c.coluna("qtd_caixas", "Caixas", "inteiro", largura=90),
]


def montar_layout():
    df = dados.carregar()
    revendas = df[["revenda_id", "revenda"]].drop_duplicates().sort_values("revenda_id")
    opcoes_revenda = [{"label": f"{r.revenda_id} · {r.revenda}", "value": r.revenda_id} for r in revendas.itertuples()]

    filtros = c.barra_filtros(
        c.filtro("Revenda", dcc.Dropdown(id="ep-revenda", options=opcoes_revenda, value=20, clearable=False)),
        c.filtro("Período de venda", dcc.Dropdown(id="ep-periodo", options=[{"label": v, "value": k} for k, v in dados.PERIODOS.items()],
                                                  value="MES_ATUAL", clearable=False)),
        c.filtro("Marca", c.dropdown("ep-marca", options=opcoes(df["marca"]))),
        c.filtro("Categoria", c.dropdown("ep-categoria", options=opcoes(df["categoria"]))),
        c.filtro("Produto", c.dropdown("ep-produto", options=[
            {"label": f"{p.produto_id} – {p.produto}", "value": p.produto_id}
            for p in df[["produto_id", "produto"]].drop_duplicates().sort_values("produto_id").itertuples()])),
        dbc.Col(c.filtro("Base do estoque", c.pilulas("ep-base", [{"label": v, "value": k} for k, v in dados.BASES.items()], "SISTEMA")),
                xs=12, md="auto"),
        dbc.Col(c.filtro("Ação", c.pilulas("ep-acao", [{"label": v, "value": k} for k, v in dados.ACOES.items()], "TODOS")),
                xs=12, md="auto"),
        dbc.Col(c.botao("Limpar filtros", "ep-limpar"), xs="auto", className="ms-md-auto"),
    )

    gauges = dbc.Row(className="g-3", children=[
        dbc.Col(c.secao(graficos.grafico(id, 190), titulo=titulo, className="h-100"), md=4)
        for id, titulo in [("ep-gauge-sellin", "Sell-in / sell-out (HL)"),
                           ("ep-gauge-marca", f"Dias de estoque · {dados.MARCA_PRINCIPAL}"),
                           ("ep-gauge-geral", "Dias de estoque · geral")]
    ])

    tabela = c.secao(
        c.barra_tabela("Reposição por produto",
                       c.botao("⬇ Exportar", "ep-exportar"), c.botao("📅 Snapshots", "ep-abrir-snapshots"), nota_id="ep-contagem"),
        c.grade("ep-grade", COLUNAS, getRowId="params.data.produto_id"),
        c.nota(f"Faixa: mínimo = média x {dados.FAIXA_DDE[0]} dias úteis, máximo = média x {dados.FAIXA_DDE[1]}. "
               "Clique em 'Em trânsito' ou 'Transf. após compra' para ver as notas."),
        dcc.Download(id="ep-download"),
    )

    detalhe = c.modal("ep-detalhe", "Produto", [
        html.H3("Em trânsito (sem entrada na revenda)", className="h6 fw-semibold mb-0"),
        c.grade("ep-grade-notas", COLUNAS_NOTAS, altura=200),
        html.H3("Transferências recebidas depois da última compra", className="h6 fw-semibold mb-0"),
        c.grade("ep-grade-recebidas", COLUNAS_RECEBIDAS, altura=200),
    ])

    snapshots = c.modal("ep-snap", "Snapshots diários", [
        dbc.Row(className="g-3 align-items-end", children=[
            dbc.Col(c.filtro("Data do snapshot", dcc.Dropdown(id="ep-snap-data", clearable=False)), xs=12, md=3),
            dbc.Col(html.Span(id="ep-snap-filtros", className=c.NOTA), xs=12, md=True),
            dbc.Col(c.botao("⬇ Exportar snapshot", "ep-snap-exportar"), xs="auto"),
        ]),
        dbc.Spinner(dbc.Row(id="ep-snap-resumo", className="g-3"), color="primary"),
        c.grade("ep-snap-grade", COLUNAS, altura=380),
        dcc.Download(id="ep-snap-download"),
    ])

    return html.Div([
        c.cabecalho("Estoque e Reposição", "Saldo, cobertura, trânsito e necessidade de reposição", "/estoque/"),
        c.conteudo(
            filtros, c.linha_cards("ep-cards"), gauges, tabela,
            c.rodape_dados(data_geracao("estoque_reposicao"), data_referencia()),
        ),
        detalhe, snapshots,
    ])
