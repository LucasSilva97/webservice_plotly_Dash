"""Extração e carga (EL): fontes locais -> schema raw do DuckDB.

A camada raw é uma cópia fiel da origem, sem regra de negócio: colunas listadas
explicitamente, tipos da origem (datas continuam texto) e uma coluna de auditoria
`_extraido_em`. Toda regra fica no dbt.

Duas formas de carga, as duas idempotentes:
- substituição: CREATE OR REPLACE da tabela inteira, numa transação;
- janela (pedidos e itens): apaga os últimos N meses e recarrega só eles. Com a tabela
  vazia, ou com completo=True, carrega o histórico inteiro.
"""
import logging
import sqlite3
from contextlib import closing
from datetime import datetime

import duckdb
import pandas as pd

from elt import config

log = logging.getLogger(__name__)

# tabela raw -> consulta na origem (ERP fictício em SQLite)
EXTRACOES = {
    "revendas": "SELECT revenda_id, nome, cidade, tipo FROM revendas",
    "vendedores": "SELECT vendedor_id, revenda_id, nome, ativo FROM vendedores",
    "clientes": """SELECT cliente_id, revenda_id, razao_social, fantasia, tipo_pessoa, canal, classe,
                          classificacao, cidade, bairro, data_cadastro, data_bloqueio,
                          condicao_pagamento_id, limite_credito FROM clientes""",
    "clientes_vendedor_hist": "SELECT cliente_id, vendedor_id, vigente_desde FROM clientes_vendedor_hist",
    "condicoes_pagamento": "SELECT condicao_pagamento_id, descricao, dias FROM condicoes_pagamento",
    "produtos": """SELECT produto_id, descricao, marca, fabricante, categoria, canal,
                          unidades_por_caixa, litros_por_caixa, ativo FROM produtos""",
    "tabela_custos": "SELECT revenda_id, produto_id, mes, custo_caixa FROM tabela_custos",
    "devolucoes": """SELECT devolucao_id, pedido_id, revenda_id, cliente_id, produto_id, data_devolucao,
                            qtd_caixas, valor FROM devolucoes""",
    "titulos_receber": """SELECT titulo_id, pedido_id, revenda_id, cliente_id, data_emissao, data_vencimento,
                                 valor, data_pagamento, valor_pago FROM titulos_receber""",
    "compras_itens": """SELECT nota_compra, revenda_id, fabricante, produto_id, data_emissao, data_entrada,
                               qtd_caixas, valor FROM compras_itens""",
    "transferencias": """SELECT nf_transferencia, revenda_origem, revenda_destino, produto_id, data_emissao,
                                data_entrada, qtd_caixas FROM transferencias""",
    "estoque_saldos": "SELECT revenda_id, produto_id, data_posicao, saldo_caixas FROM estoque_saldos",
    "contagens_estoque": "SELECT revenda_id, produto_id, data_contagem, qtd_contada FROM contagens_estoque",
    "equipamentos_cedidos": "SELECT cliente_id, tipo_equipamento, quantidade FROM equipamentos_cedidos",
    "solicitacoes_credito": """SELECT solicitacao_id, revenda_id, cliente_id, data_solicitacao, tipo, limite_atual,
                                      limite_solicitado, prazo_solicitado_dias, situacao, solicitante,
                                      observacao, origem FROM solicitacoes_credito""",
    "historico_implantacoes": """SELECT revenda_id, cliente_id, data_implantacao, classificacao, prazo_dias_antes,
                                        prazo_dias_depois, media_atraso, faturamento_medio, limite_antes,
                                        limite_depois FROM historico_implantacoes""",
}

# Cargas por janela: a coluna data_emissao (texto AAAA-MM-DD) define o corte.
EXTRACOES_JANELA = {
    "pedidos": """SELECT pedido_id, revenda_id, cliente_id, vendedor_id, data_emissao, condicao_pagamento_id,
                         status, valor_total FROM pedidos WHERE data_emissao >= ?""",
    "pedido_itens": """SELECT i.pedido_id, i.item, i.produto_id, i.tipo_item, i.qtd_caixas, i.valor,
                              p.data_emissao
                       FROM pedido_itens i JOIN pedidos p ON p.pedido_id = i.pedido_id
                       WHERE p.data_emissao >= ?""",
}


def inicio_janela(meses=config.JANELA_VENDAS_MESES):
    """Primeiro dia do mês que abre a janela (o mês de referência conta como o 1º)."""
    ref = pd.Timestamp(config.DATA_REFERENCIA)
    return (ref.to_period("M") - (meses - 1)).start_time.date().isoformat()


def _existe(con, tabela):
    return con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'raw' AND table_name = ?",
        [tabela]).fetchone()[0] > 0


def substituir(con, tabela, df):
    df = df.assign(_extraido_em=datetime.now().replace(microsecond=0))
    con.register("carga", df)
    con.execute("BEGIN")
    con.execute(f"CREATE OR REPLACE TABLE raw.{tabela} AS SELECT * FROM carga")
    con.execute("COMMIT")
    con.unregister("carga")


def carregar_janela(con, tabela, df, inicio):
    df = df.assign(_extraido_em=datetime.now().replace(microsecond=0))
    con.register("carga", df)
    con.execute("BEGIN")
    con.execute(f"DELETE FROM raw.{tabela} WHERE data_emissao >= ?", [inicio])
    con.execute(f"INSERT INTO raw.{tabela} SELECT * FROM carga")
    con.execute("COMMIT")
    con.unregister("carga")


def ler_planilha_metas():
    """A planilha chega como texto; a conversão do número pt-BR é feita no staging."""
    return pd.read_csv(config.PASTA_PLANILHAS / "metas_comerciais.csv", sep=";", dtype=str)


def ingerir(completo=False):
    if not config.ERP.exists():
        raise FileNotFoundError(f"Fonte não encontrada: {config.ERP}. Rode a geração das fontes antes.")
    config.BANCO.parent.mkdir(parents=True, exist_ok=True)
    resumo = {}
    origem = sqlite3.connect(config.ERP)  # o "with" do sqlite3 não fecha a conexão
    with closing(origem), duckdb.connect(str(config.BANCO)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        for tabela, consulta in EXTRACOES.items():
            df = pd.read_sql_query(consulta, origem)
            substituir(con, tabela, df)
            resumo[tabela] = (len(df), "substituição")

        for tabela, consulta in EXTRACOES_JANELA.items():
            if completo or not _existe(con, tabela) or con.execute(f"SELECT count(*) FROM raw.{tabela}").fetchone()[0] == 0:
                df = pd.read_sql_query(consulta, origem, params=["0000-00-00"])
                substituir(con, tabela, df)
                resumo[tabela] = (len(df), "histórico completo")
            else:
                inicio = inicio_janela()
                df = pd.read_sql_query(consulta, origem, params=[inicio])
                carregar_janela(con, tabela, df, inicio)
                resumo[tabela] = (len(df), f"janela desde {inicio}")

        metas = ler_planilha_metas()
        substituir(con, "metas_comerciais", metas)
        resumo["metas_comerciais"] = (len(metas), "substituição (planilha)")

    for tabela, (linhas, modo) in resumo.items():
        log.info("raw.%-24s %8d linhas  (%s)", tabela, linhas, modo)
    return resumo
