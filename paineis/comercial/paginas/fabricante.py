"""Painel do fabricante parceiro: caixas, clientes com compra e ruptura, mês a mês,
ano corrente x ano anterior x meta do programa."""
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from paineis.comercial import dados
from paineis.comum import formatos

CANAIS = [{"label": "Todos", "value": "TODOS"}] + [{"label": v, "value": k} for k, v in dados.CANAIS.items()]


def layout():
    return html.Div([
        html.Section(className="secao barra-filtros", children=[
            html.Label([html.Span("Canal"), dcc.RadioItems(id="cm-f-canal", options=CANAIS, value="TODOS", className="radio-pilula")],
                       className="filtro"),
            html.Span(f"Programa do fabricante parceiro ({dados.FABRICANTE_PROGRAMA}): só os produtos dele entram em caixas e clientes. "
                      "'Todos' conta uma vez o cliente que comprou nos dois canais.", className="nota"),
        ]),
        html.Section(className="secao", children=html.Div(id="cm-f-blocos", className="blocos-fabricante")),
    ])


def _sparkline(atual, anterior):
    meses = formatos.MESES
    figura = go.Figure()
    figura.add_scatter(x=meses, y=anterior, name="ano anterior", line={"color": "#9aa8ae", "dash": "dash"})
    figura.add_scatter(x=meses, y=atual, name="ano atual", line={"color": "#0e4d64", "width": 3}, fill="tozeroy", fillcolor="rgba(14,77,100,0.08)")
    figura.update_layout(height=110, margin={"l": 0, "r": 0, "t": 4, "b": 0}, showlegend=False, xaxis_visible=False,
                         yaxis_visible=False, plot_bgcolor="#fff", separators=",.")
    return dcc.Graph(figure=figura, config={"displayModeBar": False})


def _celula(valor, tipo="numero", destaque=False):
    if formatos.vazio(valor):
        return html.Td("—", className="cinza")
    if tipo == "pct":
        classe = "positivo" if valor >= (100 if destaque else 0) else "negativo"
        texto = ("+" if valor > 0 and not destaque else "") + formatos.pct(valor)
        return html.Td(texto, className=classe)
    if tipo == "pp":
        return html.Td(("+" if valor > 0 else "") + formatos.numero(valor, 1) + " p.p.", className="positivo" if valor >= 0 else "negativo")
    if tipo == "pct_simples":
        return html.Td(formatos.pct(valor))
    return html.Td(formatos.numero(valor))


def _tabela(linhas, com_total=True):
    cabecalho = html.Tr([html.Th("")] + [html.Th(m) for m in formatos.MESES] + ([html.Th("Total")] if com_total else []))
    corpo = []
    for rotulo, valores, tipo, destaque, total in linhas:
        celulas = [html.Td(rotulo)] + [_celula(v, tipo, destaque) for v in valores]
        if com_total:
            celula_total = _celula(total, tipo, destaque)
            celula_total.className = getattr(celula_total, "className", "") + " total"
            celulas.append(celula_total)
        corpo.append(html.Tr(celulas))
    return html.Div(className="rolagem", children=html.Table([html.Thead(cabecalho), html.Tbody(corpo)], className="tabela-simples"))


def _bloco(selo, titulo, subtitulo, atual, anterior, tabela):
    return html.Div(className="bloco-fabricante", children=[
        html.Div([
            html.Div(className="bloco-titulo", children=[html.Span(selo, className="selo"),
                                                       html.Div([html.H2(titulo), html.Span(subtitulo, className="nota")])]),
            _sparkline(atual, anterior),
        ]),
        tabela,
    ])


def registrar(app):
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
            _bloco("CX", "Caixas", "volume líquido dos produtos do fabricante", cx["atual"], cx["anterior"], caixas),
            _bloco("CL", "Clientes com compra", "Total = clientes distintos no ano até o último mês com venda", cl["atual"], cl["anterior"], clientes),
            _bloco("RP", "Ruptura da carteira", "% de clientes ativos sem compra (quanto menor, melhor)", rp["atual"], rp["anterior"], ruptura),
        ]
