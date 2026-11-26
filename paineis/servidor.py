"""Um servidor Flask com os três painéis, cada um uma aplicação Dash independente.

Cada painel tem a própria instância Dash, o próprio prefixo de URL e os próprios callbacks
(registrados com app.callback, nunca no registro global do Dash), como processos separados
teriam. Dividem só o servidor e a pasta de assets com a identidade visual.
"""
from flask import Flask

from paineis.comum import dados, formatos

PAGINA_INICIAL = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Andorinha · painéis</title><link rel="icon" href="/estoque/assets/logo.svg">
<link rel="stylesheet" href="/estoque/assets/bootstrap.min.css">
<link rel="stylesheet" href="/estoque/assets/estilo.css"></head>
<body>
<nav class="navbar navbar-dark bg-primary py-2"><div class="container-fluid px-4 gap-3">
<a class="navbar-brand d-flex align-items-center gap-2 me-2 fs-6" href="/"><img src="/estoque/assets/logo.svg" alt="" width="34" height="34">
<span><span class="d-block fw-bold lh-1">Andorinha</span><small class="d-block fw-normal opacity-75">painéis de demonstração</small></span></a>
<div class="flex-grow-1 text-white"><h1 class="h5 mb-0">Distribuidora Andorinha (fictícia)</h1>
<small class="opacity-75">Dados sintéticos publicados pelo ELT · referência {referencia}</small></div></div></nav>
<main class="container py-4">
<div class="row row-cols-1 row-cols-md-3 g-3">
{cartoes}
</div></main></body></html>"""
CARTAO = """<div class="col"><div class="card h-100 shadow-sm"><div class="card-body">
<h2 class="h6 fw-semibold"><a href="{link}" class="stretched-link text-decoration-none">{titulo}</a></h2>
<p class="card-text text-body-secondary mb-0">{texto}</p></div></div></div>"""
CARTOES = [
    ("/estoque/", "Estoque e Reposição",
     "Saldo, cobertura em dias úteis, trânsito entre unidades e quanto puxar ou reduzir por produto e revenda. Snapshot diário."),
    ("/comercial/", "Comercial",
     "Diário de vendas, metas, carteira de clientes, ruptura de cobertura e o painel do fabricante parceiro."),
    ("/credito/", "Crédito e Prazo",
     "Consulta de limite e prazo, cobrança, solicitações, histórico de implantações e pedidos do cliente."),
]


def criar_servidor():
    from paineis import comercial, credito, estoque

    servidor = Flask(__name__)
    servidor.paineis = {  # guardados para os testes chamarem os callbacks de cada um
        "estoque": estoque.criar_app(servidor),
        "comercial": comercial.criar_app(servidor),
        "credito": credito.criar_app(servidor),
    }

    @servidor.route("/")
    def inicio():
        cartoes = "\n".join(CARTAO.format(link=link, titulo=titulo, texto=texto) for link, titulo, texto in CARTOES)
        return PAGINA_INICIAL.replace("{referencia}", formatos.data(dados.data_referencia())).replace("{cartoes}", cartoes)

    return servidor
