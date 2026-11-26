"""Peças de layout usadas pelos três painéis, montadas com dash-bootstrap-components.

O visual vem do Bootstrap 5.3 (assets/bootstrap.min.css) com as cores da Andorinha aplicadas por
variáveis em assets/estilo.css. Aqui ficam só as combinações de componentes e classes utilitárias
que se repetem; as páginas usam dbc e Bootstrap diretamente no resto.
"""
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import dcc, html

from paineis.comum import formatos

MODULOS = [("Estoque e Reposição", "/estoque/"), ("Comercial", "/comercial/"), ("Crédito e Prazo", "/credito/")]
NOTA = "small text-body-secondary"
COR_DO_TOM = {"neutro": "secondary", "azul": "info", "vermelho": "danger", "verde": "success", "ambar": "warning", "escuro": "warning"}


def cabecalho(titulo, subtitulo, atual):
    """Barra superior com a marca da demonstração e os links para os outros painéis.
    Os links são externos: cada painel é outra aplicação Dash, então a página recarrega."""
    return dbc.Navbar(color="primary", dark=True, className="py-2", children=dbc.Container(fluid=True, className="px-4 gap-3", children=[
        dbc.NavbarBrand(href="/", external_link=True, className="d-flex align-items-center gap-2 me-2 fs-6", children=[
            html.Img(src="assets/logo.svg", alt="", width=34, height=34),
            html.Span([html.Span("Andorinha", className="d-block fw-bold lh-1"),
                       html.Small("painéis de demonstração", className="d-block fw-normal opacity-75")]),
        ]),
        html.Div(className="flex-grow-1 text-white", children=[
            html.H1(titulo, className="h5 mb-0"), html.Small(subtitulo, className="opacity-75"),
        ]),
        dbc.Nav(pills=True, className="modulos gap-1", children=[
            dbc.NavItem(dbc.NavLink(nome, href=link, active=link == atual, external_link=True,
                                    className="rounded-pill border border-light border-opacity-25 py-1 small"))
            for nome, link in MODULOS
        ]),
    ]))


def conteudo(*filhos):
    """Área principal da página: as seções empilhadas com espaço entre elas."""
    return html.Main(className="container-fluid px-4 pt-3 pb-4 vstack gap-3", children=list(filhos))


def secao(*filhos, titulo=None, className="", **props):
    """Bloco branco da página (um card do Bootstrap), com título opcional."""
    corpo = ([html.H2(titulo, className="h6 fw-semibold mb-2")] if titulo else []) + list(filhos)
    return dbc.Card(dbc.CardBody(corpo), className=f"shadow-sm {className}".strip(), **props)


def abas(id):
    """Abas das páginas (Comercial e Crédito); o callback de rota preenche com links_abas()."""
    return dbc.Nav(id=id, className="nav-underline border-bottom")


def links_abas(itens):
    """itens: (titulo, href, ativo). Navegação dentro do mesmo painel, sem recarregar."""
    return [dbc.NavItem(dbc.NavLink(titulo, href=href, active=ativo)) for titulo, href, ativo in itens]


def barra_pagina(abas_, *direita):
    """Linha com as abas à esquerda e um filtro global (revenda) à direita."""
    return html.Div(className="d-flex flex-wrap justify-content-between align-items-end gap-3", children=[abas_, *direita])


def card(titulo, valor, detalhe=None, tom="neutro", id=None):
    """Indicador simples, já dentro da coluna da linha de cards. tom: neutro, azul, vermelho, verde, ambar, escuro."""
    filhos = [html.Div(titulo, className="small fw-semibold text-uppercase opacity-75"),
              html.Div(valor, className="fs-4 fw-bold lh-sm")]
    if detalhe:
        filhos.append(html.Div(detalhe, className="small opacity-75"))
    classes = f"tom-{tom} h-100 shadow-sm border-0 border-start border-4 border-{COR_DO_TOM.get(tom, 'secondary')}"
    if tom == "escuro":
        classes += " text-bg-primary"
    props = {"id": id} if id else {}
    return dbc.Col(dbc.Card(dbc.CardBody(filhos, className="py-2 px-3"), className=classes, **props), xs=6, md=4, xl=True)


def linha_cards(id):
    """Linha que recebe os card() de um callback."""
    return dbc.Row(id=id, className="g-3")


def rodape_dados(gerado_em, referencia):
    texto = "Sem dados publicados"
    if gerado_em:
        texto = f"Dados publicados em {gerado_em:%d/%m/%Y %H:%M}"
    if referencia:
        texto += f" · data de referência {formatos.data(referencia)}"
    return html.Small(texto, className="text-body-secondary")


def filtro(rotulo, componente):
    return html.Div([dbc.Label(rotulo, className="small fw-semibold text-body-secondary mb-1"), componente])


def barra_filtros(*itens):
    """Filtros lado a lado, quebrando linha conforme a largura. Quem precisa de outra largura
    (botões, notas, pílulas) entra já como dbc.Col."""
    colunas = [i if isinstance(i, dbc.Col) else dbc.Col(i, xs=12, sm=6, md=4, lg=3, xl=2) for i in itens]
    return secao(dbc.Row(colunas, className="g-3 align-items-end"))


def dropdown(id, multi=True, **kwargs):
    return dcc.Dropdown(id=id, multi=multi, placeholder="Todos", **kwargs)


def pilulas(id, opcoes, valor):
    """Escolha única como grupo de botões. opcoes: lista de valores ou de {label, value}."""
    opcoes = [o if isinstance(o, dict) else {"label": o, "value": o} for o in opcoes]
    return html.Div(className="grupo-pilulas", children=dbc.RadioItems(
        id=id, options=opcoes, value=valor, className="btn-group flex-wrap",
        inputClassName="btn-check", labelClassName="btn btn-sm btn-outline-primary", labelCheckedClassName="active"))


def botao(texto, id, principal=False, **kwargs):
    """Botão do painel: contorno (secundário) por padrão, cheio quando é a ação principal."""
    return dbc.Button(texto, id=id, color="primary", outline=not principal, size="sm", **kwargs)


def barra_tabela(titulo, *acoes, nota_id=None):
    """Título da tabela (com uma nota opcional preenchida por callback) e os botões à direita."""
    cabeca = titulo if not isinstance(titulo, str) else html.H2(titulo, className="h6 fw-semibold mb-0")
    esquerda = html.Div([cabeca, html.Span(id=nota_id, className=NOTA)]) if nota_id else cabeca
    return html.Div(className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2",
                    children=[esquerda, html.Div(list(acoes), className="d-flex gap-2")])


def nota(texto, **props):
    return html.P(texto, className=f"{NOTA} mb-0 mt-2", **props)


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


def modal(id, titulo, conteudo, tamanho="xl"):
    """Janela sobreposta (dbc.Modal). Abre com is_open=True; o X, o Esc e o clique fora fecham."""
    return dbc.Modal(id=id, is_open=False, size=tamanho, scrollable=True, children=[
        dbc.ModalHeader(dbc.ModalTitle(titulo, id=f"{id}-titulo", className="h5")),
        dbc.ModalBody(conteudo, className="vstack gap-3"),
    ])
