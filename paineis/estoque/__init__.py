"""Painel de Estoque e Reposição (/estoque/)."""
from dash import Dash

from paineis.comum.dados import RAIZ


def criar_app(servidor):
    from paineis.estoque import callbacks, layout

    app = Dash(__name__, server=servidor, url_base_pathname="/estoque/",
               assets_folder=str(RAIZ / "paineis" / "assets"), title="Estoque e Reposição · Andorinha",
               suppress_callback_exceptions=True, update_title=None)
    app.layout = layout.montar_layout  # função: reavaliada a cada carga da página
    callbacks.registrar(app)
    return app
