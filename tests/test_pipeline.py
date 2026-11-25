"""Pipeline: gerador reproduzível, carga sem duplicar, reexecução igual e implantação de crédito local.

Tudo roda em pastas temporárias (o data/ do projeto não é tocado), trocando os caminhos de
elt/config.py.
"""
import json
import shutil
import sqlite3
from contextlib import closing

import duckdb
import pandas as pd
import pytest

from elt import __main__ as elt_main
from elt import config, credito_implantacao, gerar_fontes, ingestao


def apontar_para(monkeypatch, pasta):
    monkeypatch.setattr(config, "PASTA_FONTES", pasta / "fontes")
    monkeypatch.setattr(config, "ERP", pasta / "fontes" / "erp.sqlite")
    monkeypatch.setattr(config, "PASTA_PLANILHAS", pasta / "fontes" / "planilhas")
    monkeypatch.setattr(config, "BANCO", pasta / "warehouse" / "distribuidora.duckdb")
    monkeypatch.setattr(config, "PASTA_PUBLICADO", pasta / "publicado")
    monkeypatch.setattr(config, "PASTA_SNAPSHOTS", pasta / "snapshots")
    monkeypatch.setattr(config, "PASTA_LOGS", pasta / "logs")


def tabelas_do_erp(caminho):
    with closing(sqlite3.connect(caminho)) as con:
        nomes = [n for (n,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {n: pd.read_sql_query(f"SELECT * FROM {n}", con) for n in nomes}


def test_gerador_reproduzivel(tmp_path, monkeypatch):
    resultados = []
    for rodada in ("a", "b"):
        apontar_para(monkeypatch, tmp_path / rodada)
        gerar_fontes.gerar()
        resultados.append((tabelas_do_erp(config.ERP), (config.PASTA_PLANILHAS / "metas_comerciais.csv").read_bytes()))
    (tabelas_a, metas_a), (tabelas_b, metas_b) = resultados
    assert metas_a == metas_b
    assert tabelas_a.keys() == tabelas_b.keys()
    for nome in tabelas_a:
        pd.testing.assert_frame_equal(tabelas_a[nome], tabelas_b[nome], obj=nome)
    # chaves consistentes entre os domínios
    clientes = set(tabelas_a["clientes"]["cliente_id"])
    assert set(tabelas_a["pedidos"]["cliente_id"]) <= clientes
    assert set(tabelas_a["titulos_receber"]["pedido_id"]) <= set(tabelas_a["pedidos"]["pedido_id"])
    assert set(tabelas_a["pedido_itens"]["produto_id"]) <= set(tabelas_a["produtos"]["produto_id"])


def test_carga_por_janela_nao_duplica(tmp_path, monkeypatch):
    if not config.ERP.exists():
        pytest.skip("Rode `python -m elt` para gerar as fontes.")
    erp, planilhas = config.ERP, config.PASTA_PLANILHAS
    apontar_para(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "ERP", erp)  # só lê as fontes do projeto; o banco é temporário
    monkeypatch.setattr(config, "PASTA_PLANILHAS", planilhas)
    ingestao.ingerir(completo=True)
    for _ in range(2):
        resumo = ingestao.ingerir()
        assert resumo["pedidos"][1].startswith("janela desde")
    with closing(sqlite3.connect(erp)) as origem, duckdb.connect(str(config.BANCO)) as con:
        for tabela, chave in [("pedidos", "pedido_id"), ("pedido_itens", "pedido_id, item")]:
            na_fonte = origem.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
            na_raw, distintos = con.execute(f"SELECT count(*), count(DISTINCT ({chave})) FROM raw.{tabela}").fetchone()
            assert na_raw == distintos == na_fonte, tabela


@pytest.mark.lento
def test_reexecucao_publica_o_mesmo_resultado(tmp_path, monkeypatch):
    apontar_para(monkeypatch, tmp_path)
    manifestos = []
    for argumentos in ([], ["--manter-fontes"], []):  # completo, janela, completo de novo
        elt_main.main(argumentos)
        manifestos.append(json.loads((config.PASTA_PUBLICADO / "_manifesto.json").read_text(encoding="utf-8")))
    assert manifestos[0]["marts"] == manifestos[1]["marts"] == manifestos[2]["marts"]
    with duckdb.connect(str(config.BANCO)) as con:
        # o snapshot do dia foi regravado três vezes e continua com uma posição só
        linhas, dias = con.execute("SELECT count(*), count(DISTINCT data_snapshot) FROM snapshots.estoque_reposicao_diario").fetchone()
    assert dias == 1 and linhas == manifestos[0]["marts"]["estoque_reposicao"]["linhas"]


def test_implantacao_de_credito_grava_so_no_erp_local(tmp_path, monkeypatch):
    if not (config.PASTA_PUBLICADO / "credito_alteracao.parquet").exists():
        pytest.skip("Rode `python -m elt` antes.")
    copia = tmp_path / "erp.sqlite"
    shutil.copy(config.ERP, copia)
    monkeypatch.setattr(config, "ERP", copia)
    proposta = pd.read_parquet(config.PASTA_PUBLICADO / "credito_alteracao.parquet")
    proposta_20 = proposta[proposta["revenda_id"] == 20]

    def contar():
        with closing(sqlite3.connect(copia)) as con:
            return con.execute("SELECT count(*) FROM historico_implantacoes").fetchone()[0]

    antes = contar()
    simulacao = credito_implantacao.implantar(executar=False, revendas=[20])
    assert simulacao["situacao"].tolist() == ["simulada, nada gravado"] and contar() == antes

    feita = credito_implantacao.implantar(executar=True, revendas=[20])
    assert feita["situacao"].tolist() == ["implantada"] and contar() == antes + len(proposta_20)
    with closing(sqlite3.connect(copia)) as con:
        primeiro = proposta_20.iloc[0]
        limite = con.execute("SELECT limite_credito FROM clientes WHERE cliente_id = ?", (int(primeiro["cliente_id"]),)).fetchone()[0]
    assert limite == primeiro["limite_novo"]

    de_novo = credito_implantacao.implantar(executar=True, revendas=[20])
    assert de_novo["situacao"].iloc[0].startswith("já implantada") and contar() == antes + len(proposta_20)
