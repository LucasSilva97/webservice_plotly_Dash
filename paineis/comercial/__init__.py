"""Painel Comercial (/comercial/): cinco páginas roteadas pela URL, com a revenda escolhida
no topo valendo para todas."""
from dash import Dash, Input, Output, dcc, html

from paineis.comercial.paginas import carteira, diario, fabricante, metas, ruptura
from paineis.comum import componentes as c
from paineis.comum.dados import RAIZ, data_geracao, data_referencia, ler_parquet

PREFIXO = "/comercial/"
PAGINAS = {
    "diario": ("Diário de vendas", diario),
    "metas": ("Metas", metas),
    "carteira": ("Carteira de clientes", carteira),
    "ruptura": ("Ruptura", ruptura),
    "fabricante": ("Painel do fabricante", fabricante),
}


def resolver(caminho):
    """'/comercial/metas' -> 'metas'; vazio ou desconhecido -> None (a raiz cai no diário)."""
    slug = (caminho or "").removeprefix(PREFIXO).strip("/")
    if slug == "":
        return "diario"
    return slug if slug in PAGINAS else None


def montar_layout():
    revendas = ler_parquet("metas_mes")[["revenda_id"]].drop_duplicates().sort_values("revenda_id")
    nomes = ler_parquet("base_clientes")[["revenda_id", "revenda"]].drop_duplicates().set_index("revenda_id")["revenda"]
    opcoes = [{"label": f"{r} · {nomes.get(r, '')}", "value": r} for r in revendas["revenda_id"]]
    return html.Div([
        dcc.Location(id="cm-url"),
        c.cabecalho("Comercial", "Vendas, metas, carteira, ruptura e fabricante parceiro", PREFIXO),
        html.Main(className="conteudo", children=[
            html.Div(className="secao-cabecalho", children=[
                html.Nav(id="cm-abas", className="abas"),
                html.Div(style={"minWidth": "260px"}, children=c.filtro(
                    "Revenda", dcc.Dropdown(id="cm-revenda", options=opcoes, value=20, clearable=False, className="dropdown"))),
            ]),
            html.Div(id="cm-pagina"),
            c.rodape_dados(data_geracao("vendas_diarias"), data_referencia()),
        ]),
    ])


def criar_app(servidor):
    app = Dash(__name__, server=servidor, url_base_pathname=PREFIXO,
               assets_folder=str(RAIZ / "paineis" / "assets"), title="Comercial · Andorinha",
               suppress_callback_exceptions=True, update_title=None)
    app.layout = montar_layout

    @app.callback(Output("cm-pagina", "children"), Output("cm-abas", "children"), Input("cm-url", "pathname"))
    def rotear(caminho):
        atual = resolver(caminho)
        abas = [dcc.Link(titulo, href=f"{PREFIXO}{slug}", className="ativa" if slug == atual else "")
                for slug, (titulo, _) in PAGINAS.items()]
        if atual is None:
            return html.Div(className="secao", children=[html.H2("Página não encontrada"),
                                                         dcc.Link("Voltar ao Diário de vendas", href=f"{PREFIXO}diario")]), abas
        return PAGINAS[atual][1].layout(), abas

    for _, modulo in PAGINAS.values():
        modulo.registrar(app)
    return app
