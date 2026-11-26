"""Os três painéis, de ponta a ponta pelo HTTP do Dash, sobre os dados publicados pelo ELT.

Os cenários fictícios do gerador (elt/gerar_fontes.py, marcados com CENÁRIO) têm de aparecer
na tela: ruptura e trânsito no estoque da Litoral, meta abaixo do planejado, ruptura alta do
vendedor 203 e clientes com limite comprometido.
"""
import json
import shutil
import sqlite3

import pytest

from paineis.comercial import dados as comercial
from paineis.comum.dados import ERP_LOCAL
from paineis.credito import dados as credito
from paineis.credito import solicitacao
from paineis.credito.paginas import PAGINAS
from paineis.estoque import dados as estoque
from paineis.estoque import layout as layout_estoque
from tests.apoio import Grupo, chamar, chave, ler_xlsx

FILTROS_ESTOQUE = [20, "MES_ATUAL", "SISTEMA", None, None, None, "TODOS"]


def textos(componente):
    """Todos os textos de uma árvore de componentes serializada, em ordem."""
    if isinstance(componente, str):
        return [componente]
    if isinstance(componente, (int, float)):
        return [str(componente)]
    if isinstance(componente, list):
        return [t for item in componente for t in textos(item)]
    if isinstance(componente, dict):
        return textos(componente.get("props", {}).get("children", []))
    return []


def opcoes_do_grupo(resposta, tipo):
    """Na resposta, cada componente do grupo ALL vem com a própria chave (o id em JSON)."""
    return {json.loads(k)["campo"]: v["options"] for k, v in resposta.items() if tipo in k}


def card(cards, titulo):
    """(valor, classe) do card com esse título. Cada card vem numa coluna (dbc.Col > dbc.Card)."""
    for item in cards:
        partes = textos(item)
        if partes and partes[0] == titulo:
            return partes[1], item["props"]["children"]["props"]["className"]
    raise AssertionError(f"card {titulo!r} não encontrado")


def test_pagina_inicial_e_layouts(servidor):
    cliente, _ = servidor
    assert cliente.get("/").status_code == 200
    for prefixo in ("/estoque/", "/comercial/", "/credito/"):
        assert cliente.get(prefixo).status_code == 200
        assert cliente.get(f"{prefixo}_dash-layout").status_code == 200


# ------------------------------------------------------------------ Estoque e Reposição
def test_estoque_mostra_ruptura_transito_e_compra_antiga(servidor):
    cliente, apps = servidor
    app = apps["estoque"]
    r = chamar(cliente, "/estoque/", app, chave(app, "ep-cards.children"), FILTROS_ESTOQUE)
    linhas = {l["produto_id"]: l for l in r["ep-grade"]["rowData"]}
    assert linhas[1002]["saldo_caixas"] == 0 and linhas[1002]["em_ruptura"]
    assert linhas[1002]["qtd_transito"] == 60 and linhas[1002]["reduzir_puxar"] > 0
    assert linhas[2003]["compra_antiga"] and linhas[2003]["transf_apos_compra"] == 2
    assert card(r["ep-cards"]["children"], "Produtos em ruptura")[0] == "3"


def test_estoque_base_contagem_muda_a_reposicao():
    df = estoque.carregar()
    sistema = estoque.filtrar(df, 40, "MES_ATUAL", "SISTEMA").set_index("produto_id")
    contagem = estoque.filtrar(df, 40, "MES_ATUAL", "CONTAGEM").set_index("produto_id")
    # CENÁRIO: a contagem da Vale achou 40 caixas a menos do produto 1003, que está em excesso.
    assert sistema.loc[1003, "saldo_caixas"] - contagem.loc[1003, "saldo_caixas"] == 40
    assert contagem.loc[1003, "reduzir_puxar"] - sistema.loc[1003, "reduzir_puxar"] == 40


def test_estoque_detalhe_do_transito(servidor):
    cliente, apps = servidor
    app = apps["estoque"]
    r = chamar(cliente, "/estoque/", app, chave(app, "ep-detalhe.is_open"),
               [{"colId": "qtd_transito", "value": 60, "rowId": "1002"}], [20], disparo="ep-grade.cellClicked")
    assert r["ep-detalhe"]["is_open"] is True
    notas = r["ep-grade-notas"]["rowData"]
    assert [(n["tipo"], n["origem"], n["qtd_caixas"]) for n in notas] == [("Transferência", "Andorinha Centro", 60)]


def test_estoque_exportar_e_snapshot(servidor):
    cliente, apps = servidor
    app = apps["estoque"]
    tela = chamar(cliente, "/estoque/", app, chave(app, "ep-cards.children"), FILTROS_ESTOQUE)
    linhas = tela["ep-grade"]["rowData"]
    download = chamar(cliente, "/estoque/", app, chave(app, "ep-download.data"), [1],
                      [linhas, layout_estoque.COLUNAS, *FILTROS_ESTOQUE])["ep-download"]["data"]
    assert download["filename"].startswith("estoque_reposicao_20_")
    planilha = ler_xlsx(download)
    assert planilha.sheetnames == ["Estoque e Reposição", "Filtros"]
    folha = planilha["Estoque e Reposição"]
    assert folha.max_row == len(linhas) + 1 and folha["B1"].value == "Produto"

    datas = estoque.datas_snapshot()
    assert datas, "o ELT grava o snapshot do dia"
    snap = chamar(cliente, "/estoque/", app, chave(app, "ep-snap-resumo.children"), [datas[0]], FILTROS_ESTOQUE)
    # O snapshot do dia é a mesma posição da tela: o resumo bate com os cards.
    assert textos(snap["ep-snap-resumo"]["children"]) == textos(tela["ep-cards"]["children"])


# ------------------------------------------------------------------ Comercial
@pytest.mark.parametrize("caminho", ["/comercial/", "/comercial/diario", "/comercial/metas", "/comercial/carteira",
                                     "/comercial/ruptura", "/comercial/fabricante"])
def test_comercial_rotas(servidor, caminho):
    cliente, apps = servidor
    app = apps["comercial"]
    r = chamar(cliente, "/comercial/", app, chave(app, "cm-pagina.children"), [caminho])
    assert "Página não encontrada" not in textos(r["cm-pagina"]["children"])


def test_comercial_rota_desconhecida(servidor):
    cliente, apps = servidor
    app = apps["comercial"]
    r = chamar(cliente, "/comercial/", app, chave(app, "cm-pagina.children"), ["/comercial/nao-existe"])
    assert "Página não encontrada" in textos(r["cm-pagina"]["children"])


def test_diario_litoral_abaixo_da_meta(servidor):
    cliente, apps = servidor
    app = apps["comercial"]
    r = chamar(cliente, "/comercial/", app, chave(app, "cm-d-cards.children"), [20, None, None, None])
    valor, classe = card(r["cm-d-cards"]["children"], "Atingimento (tendência)")
    assert "tom-vermelho" in classe
    assert comercial.diario(20)[0]["ating_tendencia"] < 90  # CENÁRIO: queda da Litoral no mês
    assert comercial.diario(10)[0]["ating_tendencia"] > 90


def test_meta_segue_o_filtro_de_vendedor():
    metas = comercial.ler_parquet("metas_mes")
    mes = int(comercial.periodo_atual()["mes"])
    soma_201_202 = metas[(metas["revenda_id"] == 20) & (metas["mes"] == mes) & metas["vendedor_id"].isin([201, 202])]["meta_faturamento_total"].sum()
    assert comercial.meta(metas, 20, mes, [201, 202]) == pytest.approx(soma_201_202)
    propria = metas[(metas["revenda_id"] == 20) & (metas["mes"] == mes) & (metas["vendedor_id"] == 0)]["meta_faturamento_total"].iloc[0]
    assert comercial.meta(metas, 20, mes) == pytest.approx(propria)


def test_metas_com_linha_da_revenda_fixa(servidor):
    cliente, apps = servidor
    app = apps["comercial"]
    mes = int(comercial.periodo_atual()["mes"])
    r = chamar(cliente, "/comercial/", app, chave(app, "cm-m-cards.children"), [20, mes])
    assert r["cm-m-grade"]["dashGridOptions"]["pinnedTopRowData"][0]["vendedor"] == "Revenda (meta própria)"
    assert len(r["cm-m-grade"]["rowData"]) == 5


def test_carteira_filtros_cruzados(servidor):
    cliente, apps = servidor
    app = apps["comercial"]
    campos = list(comercial.FILTROS_CARTEIRA)
    ids = [{"campo": campo, "tipo": "cm-c-filtro"} for campo in campos]
    valores = {campo: None for campo in campos} | {"vendedor_id": [203]}
    r = chamar(cliente, "/comercial/", app, chave(app, "cm-c-cards.children"),
               [20, "Ativo", "Todos", Grupo((i, valores[i["campo"]]) for i in ids)],
               saidas_grupo={'{"campo":["ALL"],"tipo":"cm-c-filtro"}': ids})
    linhas = r["cm-c-grade"]["rowData"]
    assert linhas and {l["vendedor_id"] for l in linhas} == {203}
    opcoes = opcoes_do_grupo(r, "cm-c-filtro")
    bairros_203 = {l["bairro"] for l in linhas}
    assert {o["value"] for o in opcoes["bairro"]} == bairros_203           # a lista respeita o vendedor
    assert {o["value"] for o in opcoes["vendedor_id"]} > {203}               # e o próprio filtro não se restringe


def test_ruptura_vendedor_203_e_total():
    do_mes, total, evolucao, _ = comercial.ruptura(20, 202610)
    pior = do_mes.sort_values("perc_ruptura").iloc[-1]
    assert pior["vendedor_id"] == 203  # CENÁRIO: vendedor com baixa positivação
    assert total["clientes_ativos"] == total["clientes_cobertos"] + total["clientes_sem_compra"]
    assert total["perc_ruptura"] == pytest.approx(100 - total["perc_cobertura"])


def test_fabricante_totais_ate_o_mesmo_mes():
    f = comercial.fabricante(20, "TODOS")
    ultimo = f["ultimo_mes"]
    assert f["caixas"]["total_anterior"] == pytest.approx(sum(v for v in f["caixas"]["anterior"][:ultimo]))
    imediato = comercial.fabricante(20, "IMEDIATO")["clientes"]["atual"]
    abastecimento = comercial.fabricante(20, "ABASTECIMENTO")["clientes"]["atual"]
    for todos, i, a in list(zip(f["clientes"]["atual"], imediato, abastecimento))[:ultimo]:
        assert max(i, a) <= todos <= i + a  # quem comprou nos dois canais conta uma vez


def test_fabricante_pagina(servidor):
    cliente, apps = servidor
    app = apps["comercial"]
    r = chamar(cliente, "/comercial/", app, "cm-f-blocos.children", [20, "TODOS"])
    assert {"Caixas", "Clientes com compra", "Ruptura da carteira"} <= set(textos(r["cm-f-blocos"]["children"]))


def test_exportar_ruptura_com_total(servidor):
    cliente, apps = servidor
    app = apps["comercial"]
    tela = chamar(cliente, "/comercial/", app, chave(app, "cm-r-resumo.children"), [20, 202610, None])
    from paineis.comercial.paginas.ruptura import COLUNAS
    download = chamar(cliente, "/comercial/", app, chave(app, "cm-r-download.data"), [1],
                      [tela["cm-r-grade"]["rowData"], COLUNAS, tela["cm-r-grade"]["dashGridOptions"], 20, 202610, None])
    folha = ler_xlsx(download["cm-r-download"]["data"])["Ruptura"]
    assert folha["A2"].value == "TOTAL" and folha.max_row == 2 + 5


# ------------------------------------------------------------------ Crédito e Prazo
@pytest.mark.parametrize("slug", list(PAGINAS))
def test_credito_paginas(servidor, slug):
    cliente, apps = servidor
    app = apps["credito"]
    pagina = PAGINAS[slug]
    ids = [{"campo": campo, "tipo": "cr-filtro"} for campo in pagina.filtros]
    seletor = credito.opcoes_seletor(pagina)[0]["value"] if pagina.seletor else None
    r = chamar(cliente, "/credito/", app, chave(app, "cr-cards.children"),
               [20, seletor, None, Grupo((i, None) for i in ids)], [f"/credito/{slug}"],
               saidas_grupo={'{"campo":["ALL"],"tipo":"cr-filtro"}': ids})
    assert r["cr-grade"]["rowData"], slug
    opcoes = opcoes_do_grupo(r, "cr-filtro")
    assert set(opcoes) == set(pagina.filtros) and all(opcoes.values())

    download = chamar(cliente, "/credito/", app, chave(app, "cr-download.data"), [1],
                      [r["cr-grade"]["rowData"], pagina.colunas, f"/credito/{slug}", 20, seletor, None,
                       Grupo((i, None) for i in ids), Grupo((i, i) for i in ids)])
    folha = ler_xlsx(download["cr-download"]["data"])[pagina.titulo[:31]]
    assert folha.max_row == 1 + len(r["cr-grade"]["rowData"])


def test_credito_troca_de_aba_nao_exporta_nem_quebra(servidor):
    """Ao trocar de aba, o Dash monta a aba nova e dispara os callbacks dela sem clique nenhum."""
    from paineis.credito import layout_pagina

    cliente, apps = servidor
    app = apps["credito"]
    # O Download nasce junto do botão: assim o Dash nem chama a exportação ao montar a aba.
    for pagina in PAGINAS.values():
        ids = [getattr(c, "id", None) for c in layout_pagina(pagina)._traverse()]
        assert "cr-exportar" in ids and "cr-download" in ids
    # E, se chamar, sem clique não gera planilha.
    inicio = PAGINAS[""]
    ids_inicio = [{"campo": campo, "tipo": "cr-filtro"} for campo in inicio.filtros]
    assert chamar(cliente, "/credito/", app, chave(app, "cr-download.data"), [None],
                  [[], inicio.colunas, "/credito/", 20, None, None, Grupo((i, None) for i in ids_inicio),
                   Grupo((i, i) for i in ids_inicio)], disparo="cr-exportar.n_clicks") == {}
    # URL já na Cobrança, filtros ainda da aba Limite e prazo: espera a aba nova em vez de KeyError.
    assert chamar(cliente, "/credito/", app, chave(app, "cr-cards.children"),
                  [20, None, None, Grupo((i, None) for i in ids_inicio)], ["/credito/cobranca"],
                  saidas_grupo={'{"campo":["ALL"],"tipo":"cr-filtro"}': ids_inicio}) == {}
    # Botão de solicitação recém-montado com um cliente ainda guardado: o modal não abre sozinho.
    guardado = {"cliente_id": 20007, "revenda_id": 20, "nome": "teste", "limite_atual": 1500.0, "prazo_atual": "21 dias"}
    assert chamar(cliente, "/credito/", app, chave(app, "cr-sol.is_open"), [None, None],
                  [guardado, None, None, None, None], disparo="cr-abrir-solicitacao.n_clicks") == {}


def test_credito_limite_comprometido_e_a_vista():
    pagina = PAGINAS[""]
    df = credito.carregar(pagina, 20)
    comprometidos = df[df["limite_comprometido"]]
    assert len(comprometidos) and (comprometidos["saldo_limite"] < 0).all()
    for cliente_id in (20007, 20015):  # CENÁRIO: pararam de pagar
        linha = df[df["cliente_id"] == cliente_id].iloc[0]
        assert linha["limite_comprometido"] and linha["novo_prazo"] == "À vista" and linha["sugestao_limite"] == "À vista"


def test_credito_detalhe_de_pedidos(servidor):
    cliente, apps = servidor
    app = apps["credito"]
    linha = {"cliente_id": 20007, "revenda_id": 20, "fantasia": "teste", "limite_atual": 1500.0, "prazo_atual": "21 dias"}
    r = chamar(cliente, "/credito/", app, chave(app, "cr-detalhe.style"), [[linha]], ["/credito/"], disparo="cr-grade.selectedRows")
    assert r["cr-detalhe"]["style"] == {}
    situacoes = {p["situacao"] for p in r["cr-grade-pedidos"]["rowData"]}
    assert "Vencido" in situacoes


def test_solicitacao_grava_so_no_erp_local(tmp_path, monkeypatch):
    copia = tmp_path / "erp.sqlite"
    shutil.copy(ERP_LOCAL, copia)
    monkeypatch.setattr(solicitacao, "ERP_LOCAL", copia)
    with pytest.raises(ValueError):
        solicitacao.registrar(20, 20003, 3000.0, None, None, "V201", "")
    numero = solicitacao.registrar(20, 20003, 3000.0, 6000, 14, "V201", "teste")
    with sqlite3.connect(copia) as con:
        linha = con.execute("SELECT tipo, situacao, origem, limite_solicitado FROM solicitacoes_credito WHERE solicitacao_id = ?",
                            (numero,)).fetchone()
    assert linha == ("Limite e prazo", "Em análise", "painel", 6000.0)


def test_solicitacao_sem_erp_local_avisa_e_nao_cria_arquivo(tmp_path, monkeypatch):
    """Na publicação online só os Parquet vão para o servidor: sem ERP local, a solicitação é recusada
    com uma mensagem (ValueError, que o painel mostra), e nenhum banco vazio é criado."""
    ausente = tmp_path / "erp.sqlite"
    monkeypatch.setattr(solicitacao, "ERP_LOCAL", ausente)
    with pytest.raises(ValueError, match="só para consulta"):
        solicitacao.registrar(20, 20003, 3000.0, 6000, 14, "V201", "teste")
    assert not ausente.exists()


def test_app_da_hospedagem_serve_os_tres_paineis(publicado, monkeypatch):
    """app.py (entrada do Posit Connect Cloud): `app` é um objeto Dash, chamado direto como WSGI
    (app:app), e atende a página inicial e os três painéis, mesmo com o prefixo de URL que
    hospedagens de Dash exportam no ambiente."""
    import importlib.util

    from dash import Dash
    from werkzeug.test import Client

    from paineis.comum.dados import RAIZ

    monkeypatch.setenv("DASH_REQUESTS_PATHNAME_PREFIX", "/")
    monkeypatch.setenv("DASH_URL_BASE_PATHNAME", "/")
    especificacao = importlib.util.spec_from_file_location("app_hospedagem", RAIZ / "app.py")
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)

    assert isinstance(modulo.app, Dash) and modulo.app.server is modulo.server
    cliente = Client(modulo.app)
    for caminho in ("/", "/estoque/", "/comercial/", "/credito/",
                    "/estoque/_dash-layout", "/comercial/_dash-layout", "/credito/_dash-layout"):
        assert cliente.get(caminho).status_code == 200, caminho
