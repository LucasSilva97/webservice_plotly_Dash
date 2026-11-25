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
<link rel="stylesheet" href="/estoque/assets/estilo.css"></head>
<body>
<header class="topo"><a class="marca" href="/"><img src="/estoque/assets/logo.svg" alt="">
<span>Andorinha<small>painéis de demonstração</small></span></a>
<div class="titulo-modulo"><h1>Distribuidora Andorinha (fictícia)</h1>
<span>Dados sintéticos publicados pelo ELT · referência {referencia}</span></div></header>
<main class="conteudo inicio">
<div class="inicio-cartoes">
<a href="/estoque/"><section class="secao"><h2>Estoque e Reposição</h2>
<p>Saldo, cobertura em dias úteis, trânsito entre unidades e quanto puxar ou reduzir por produto e revenda. Snapshot diário.</p></section></a>
<a href="/comercial/"><section class="secao"><h2>Comercial</h2>
<p>Diário de vendas, metas, carteira de clientes, ruptura de cobertura e o painel do fabricante parceiro.</p></section></a>
<a href="/credito/"><section class="secao"><h2>Crédito e Prazo</h2>
<p>Consulta de limite e prazo, cobrança, solicitações, histórico de implantações e pedidos do cliente.</p></section></a>
</div></main></body></html>"""


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
        return PAGINA_INICIAL.replace("{referencia}", formatos.data(dados.data_referencia()))

    return servidor
