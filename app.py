"""Ponto de entrada para hospedagem: Posit Connect Cloud (framework Dash) ou qualquer servidor WSGI.

O Connect Cloud procura, no arquivo principal, um objeto Dash chamado `app`. Os três painéis dividem
um servidor Flask; `app` é o painel de Estoque, e o servidor dele (app.server) atende também a página
inicial, /comercial/ e /credito/. Os dados vêm de data/publicado/, versionado no repositório.

Nesta máquina continue usando paineis.bat (ou python -m paineis); este arquivo é só para a nuvem.
Teste local do mesmo jeito que a hospedagem carrega: waitress-serve --port 8050 app:app
"""
import os

# Cada painel define o próprio prefixo de URL (/estoque/, /comercial/, /credito/). Hospedagens de Dash
# costumam exportar um prefixo único para "o" app, e o Dash recusa prefixo duplo (InvalidConfig).
# O conteúdo é servido na raiz do próprio endereço, então essas variáveis são descartadas.
for _variavel in ("DASH_URL_BASE_PATHNAME", "DASH_REQUESTS_PATHNAME_PREFIX", "DASH_ROUTES_PATHNAME_PREFIX"):
    os.environ.pop(_variavel, None)

from paineis.servidor import criar_servidor  # noqa: E402  (depois de limpar o ambiente)

server = criar_servidor()
app = server.paineis["estoque"]

if __name__ == "__main__":
    from waitress import serve

    serve(server, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)), threads=8)
