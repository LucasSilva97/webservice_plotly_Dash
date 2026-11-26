"""Painel do fabricante parceiro: caixas, clientes com compra e ruptura, mês a mês,
ano corrente x ano anterior x meta do programa."""
import dash_bootstrap_components as dbc
from dash import Input, Output, html

from paineis.comercial import dados
from paineis.comum import componentes as c
from paineis.comum import formatos, graficos

POSITIVO, NEGATIVO = "text-success fw-semibold", "text-danger fw-semibold"
SPARKLINES = ("cm-f-spark-caixas", "cm-f-spark-clientes", "cm-f-spark-ruptura")
CANAIS = [{"label": "Todos", "value": "TODOS"}] + [{"label": v, "value": k} for k, v in dados.CANAIS.items()]


def layout():
    return html.Div(className="vstack gap-3", children=[
        c.barra_filtros(
            dbc.Col(c.filtro("Canal", c.pilulas("cm-f-canal", CANAIS, "TODOS")), xs=12, md="auto"),
            dbc.Col(html.Span(f"Programa do fabricante parceiro ({dados.FABRICANTE_PROGRAMA}): só os produtos dele entram em caixas "
                              "e clientes. 'Todos' conta uma vez o cliente que comprou nos dois canais.", className=c.NOTA), xs=12, md=True),
        ),
        c.secao(html.Div(id="cm-f-blocos", className="vstack gap-4")),
    ])


def _sparkline(id, atual, anterior, formato):
    """Linha do ano atual (com área) sobre a do ano anterior, sem eixos; o mês aparece no tooltip."""
    linha = {"type": "line", "symbol": "circle", "symbolSize": 5, "showSymbol": False}
    opcao = graficos.opcao(
        grid={"left": 2, "right": 2, "top": 6, "bottom": 2},
        tooltip={**graficos.TOOLTIP_EIXO, "axisPointer": {"type": "line"}, "valueFormatter": f"fn:{formato}"},
        xAxis={"type": "category", "data": formatos.MESES, "show": False, "boundaryGap": False},
        yAxis={"type": "value", "show": False, "scale": True},
        series=[
            {**linha, "id": "anterior", "name": "ano anterior", "data": graficos.valores(anterior),
             "lineStyle": {"color": graficos.CINZA_LINHA, "type": "dashed", "width": 2}, "itemStyle": {"color": graficos.CINZA_LINHA}},
            {**linha, "id": "atual", "name": "ano atual", "data": graficos.valores(atual),
             "lineStyle": {"color": graficos.AZUL, "width": 3}, "itemStyle": {"color": graficos.AZUL},
             "areaStyle": {"color": "rgba(14,77,100,0.08)"}},
        ],
    )
    return graficos.grafico(id, 110, opcao)


def _celula(valor, tipo="numero", destaque=False):
    if formatos.vazio(valor):
        return html.Td("—", className="text-body-secondary")
    if tipo == "pct":
        classe = POSITIVO if valor >= (100 if destaque else 0) else NEGATIVO
        texto = ("+" if valor > 0 and not destaque else "") + formatos.pct(valor)
        return html.Td(texto, className=classe)
    if tipo == "pp":
        return html.Td(("+" if valor > 0 else "") + formatos.numero(valor, 1) + " p.p.", className=POSITIVO if valor >= 0 else NEGATIVO)
    if tipo == "pct_simples":
        return html.Td(formatos.pct(valor))
    return html.Td(formatos.numero(valor))


def _tabela(linhas, com_total=True):
    cabecalho = html.Tr([html.Th("", className="text-start")] + [html.Th(m) for m in formatos.MESES] + ([html.Th("Total")] if com_total else []))
    corpo = []
    for rotulo, valores, tipo, destaque, total in linhas:
        celulas = [html.Td(rotulo, className="text-start")] + [_celula(v, tipo, destaque) for v in valores]
        if com_total:
            celula_total = _celula(total, tipo, destaque)
            celula_total.className = (getattr(celula_total, "className", None) or "") + " fw-semibold bg-body-tertiary"
            celulas.append(celula_total)
        corpo.append(html.Tr(celulas))
    return dbc.Table([html.Thead(cabecalho, className="table-primary"), html.Tbody(corpo)],
                     size="sm", hover=True, responsive=True, className="text-end text-nowrap mb-0")


def _bloco(selo, titulo, subtitulo, sparkline, tabela):
    return dbc.Row(className="align-items-center g-3", children=[
        dbc.Col(lg=3, children=[
            html.Div(className="d-flex align-items-center gap-2", children=[
                html.Span(selo, className="rounded-circle bg-primary text-warning fw-bolder d-flex align-items-center "
                                          "justify-content-center flex-shrink-0", style={"width": "40px", "height": "40px"}),
                html.Div([html.H2(titulo, className="h6 fw-semibold mb-0"), html.Span(subtitulo, className=c.NOTA)]),
            ]),
            sparkline,
        ]),
        dbc.Col(tabela, lg=9),
    ])


def registrar(app):
    graficos.registrar(app, *SPARKLINES)

    @app.callback(Output("cm-f-blocos", "children"), Input("cm-revenda", "value"), Input("cm-f-canal", "value"))
    def atualizar(revenda, canal):
        f = dados.fabricante(revenda, canal)
        ano, cx, cl, rp = f["ano"], f["caixas"], f["clientes"], f["ruptura"]
        caixas = _tabela([
            (str(ano), cx["atual"], "numero", False, cx["total_atual"]),
            (str(ano - 1), cx["anterior"], "numero", False, cx["total_anterior"]),
            ("% crescimento", cx["crescimento"], "pct", False, dados.pct(cx["total_atual"] - cx["total_anterior"], cx["total_anterior"])),
            ("Meta", cx["meta"], "numero", False, cx["total_meta"]),
            ("% atingimento", cx["atingimento"], "pct", True, dados.pct(cx["total_atual"], cx["total_meta"])),
        ])
        clientes = _tabela([
            (str(ano), cl["atual"], "numero", False, cl["total_atual"]),
            (str(ano - 1), cl["anterior"], "numero", False, cl["total_anterior"]),
            ("% crescimento", cl["crescimento"], "pct", False, dados.pct((cl["total_atual"] or 0) - (cl["total_anterior"] or 0), cl["total_anterior"])),
            ("Meta", cl["meta"], "numero", False, None),
            ("% atingimento", cl["atingimento"], "pct", True, None),
        ])
        ruptura = _tabela([
            (str(ano), rp["atual"], "pct_simples", False, None),
            (str(ano - 1), rp["anterior"], "pct_simples", False, None),
            ("Melhoria", rp["melhoria"], "pp", False, None),
            ("Meta", rp["meta"], "pct_simples", False, None),
        ], com_total=False)
        return [
            _bloco("CX", "Caixas", "volume líquido dos produtos do fabricante", _sparkline(SPARKLINES[0], cx["atual"], cx["anterior"], "inteiro"), caixas),
            _bloco("CL", "Clientes com compra", "Total = clientes distintos no ano até o último mês com venda", _sparkline(SPARKLINES[1], cl["atual"], cl["anterior"], "inteiro"), clientes),
            _bloco("RP", "Ruptura da carteira", "% de clientes ativos sem compra (quanto menor, melhor)", _sparkline(SPARKLINES[2], rp["atual"], rp["anterior"], "pct"), ruptura),
        ]
