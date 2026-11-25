"""Peças de layout usadas pelos três painéis."""
import dash_ag_grid as dag
from dash import dcc, html

from paineis.comum import formatos

MODULOS = [("Estoque e Reposição", "/estoque/"), ("Comercial", "/comercial/"), ("Crédito e Prazo", "/credito/")]


def cabecalho(titulo, subtitulo, atual):
    """Barra superior com a marca da demonstração e os links para os outros painéis."""
    return html.Header(className="topo", children=[
        html.A(href="/", className="marca", children=[
            html.Img(src="assets/logo.svg", alt=""),
            html.Span(["Andorinha", html.Small("painéis de demonstração")]),
        ]),
        html.Div(className="titulo-modulo", children=[html.H1(titulo), html.Span(subtitulo)]),
        html.Nav(className="modulos", children=[
            html.A(nome, href=link, className="ativo" if link == atual else "") for nome, link in MODULOS
        ]),
    ])


def card(titulo, valor, detalhe=None, tom="neutro", id=None):
    """Indicador simples. tom: neutro, azul, vermelho, verde, ambar."""
    filhos = [html.Span(titulo, className="card-titulo"), html.Strong(valor, className="card-valor")]
    if detalhe:
        filhos.append(html.Span(detalhe, className="card-detalhe"))
    props = {"id": id} if id else {}
    return html.Div(filhos, className=f"card tom-{tom}", **props)


def rodape_dados(gerado_em, referencia):
    texto = "Sem dados publicados"
    if gerado_em:
        texto = f"Dados publicados em {gerado_em:%d/%m/%Y %H:%M}"
    if referencia:
        texto += f" · data de referência {formatos.data(referencia)}"
    return html.Span(texto, className="dados-de")


def filtro(rotulo, componente):
    return html.Label([html.Span(rotulo), componente], className="filtro")


def dropdown(id, multi=True, **kwargs):
    return dcc.Dropdown(id=id, multi=multi, placeholder="Todos", className="dropdown", **kwargs)


TEXTOS_GRADE = {  # textos do AG Grid em português
    "page": "Página", "of": "de", "to": "a", "more": "mais", "first": "Primeira", "last": "Última",
    "next": "Próxima", "previous": "Anterior", "pageSizeSelectorLabel": "Linhas por página:",
    "noRowsToShow": "Nenhuma linha", "loadingOoo": "Carregando...", "filterOoo": "Filtrar...",
    "equals": "Igual a", "notEqual": "Diferente de", "contains": "Contém", "notContains": "Não contém",
    "startsWith": "Começa com", "endsWith": "Termina com", "lessThan": "Menor que", "greaterThan": "Maior que",
    "lessThanOrEqual": "Menor ou igual a", "greaterThanOrEqual": "Maior ou igual a", "inRange": "Entre",
    "blank": "Vazio", "notBlank": "Preenchido", "andCondition": "E", "orCondition": "OU",
    "pinColumn": "Fixar coluna", "autosizeThisColumn": "Ajustar esta coluna", "autosizeAllColumns": "Ajustar todas",
    "resetColumns": "Restaurar colunas",
}


def grade(id, colunas, altura=520, dashGridOptions=None, **kwargs):
    """AG Grid com os padrões dos painéis (ordenar, filtrar, redimensionar; números em pt-BR)."""
    return dag.AgGrid(
        id=id,
        columnDefs=colunas,
        rowData=[],
        defaultColDef={"sortable": True, "filter": True, "resizable": True, "minWidth": 90},
        dashGridOptions={"animateRows": False, "localeText": TEXTOS_GRADE,
                         "paginationPageSizeSelector": [25, 50, 100], **(dashGridOptions or {})},
        style={"height": f"{altura}px", "width": "100%"},
        className="ag-theme-quartz grade",
        **kwargs,
    )


def coluna(campo, titulo, formato=None, largura=None, **extra):
    """Definição de coluna do AG Grid. formato: inteiro, dec1, dec2, moeda, pct, data."""
    definicao = {"field": campo, "headerName": titulo}
    if formato:
        definicao["valueFormatter"] = {"function": f"{formato}(params.value)"}
        if formato != "data":
            definicao["type"] = "rightAligned"
            definicao["filter"] = "agNumberColumnFilter"
    if largura:
        definicao["width"] = largura
    definicao.update(extra)
    return definicao


def modal(id, titulo, conteudo, largura="960px"):
    """Janela sobreposta simples; abre e fecha trocando a classe do fundo."""
    return html.Div(id=f"{id}-fundo", className="modal-fundo oculto", children=[
        html.Div(className="modal", style={"maxWidth": largura}, children=[
            html.Div(className="modal-topo", children=[
                html.H2(titulo, id=f"{id}-titulo"),
                html.Button("✕", id=f"{id}-fechar", className="botao-fechar", title="Fechar"),
            ]),
            html.Div(conteudo, className="modal-corpo"),
        ]),
    ])
