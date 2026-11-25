"""Publicação: cada mart do dbt vira um arquivo Parquet em data/publicado/.

Os painéis leem só estes arquivos; nenhum deles abre o banco. O arquivo é gravado num
temporário e trocado de uma vez (os.replace), para o painel nunca ler um arquivo pela metade.
Mart vazio não é publicado: o arquivo anterior fica, e o pipeline falha com a mensagem.

O manifesto (_manifesto.json) guarda linhas e um hash do conteúdo de cada arquivo. É ele que
prova que duas execuções com a mesma entrada publicaram o mesmo resultado.
"""
import hashlib
import json
import logging
import os
import time

import duckdb

from elt import config

log = logging.getLogger(__name__)

# mart -> colunas do grão (ordenam o arquivo, para o conteúdo sair igual a cada execução)
MARTS = {
    # Estoque
    "estoque_reposicao": ["revenda_id", "produto_id", "periodo", "base_estoque"],
    "estoque_transito_notas": ["revenda_id", "produto_id", "tipo", "documento"],
    "estoque_transferencias_recebidas": ["revenda_id", "produto_id", "nf_transferencia"],
    "sellin_sellout_mes": ["revenda_id", "produto_id", "mes"],
    # Comercial
    "periodo_analise": ["mes"],
    "vendas_diarias": ["revenda_id", "data", "vendedor_id", "produto_id"],
    "positivacao_cliente_mes": ["revenda_id", "mes", "cliente_id", "vendedor_id", "canal"],
    "metas_mes": ["revenda_id", "mes", "vendedor_id"],
    "ruptura_vendedor_mes": ["revenda_id", "mes", "vendedor_id"],
    "base_clientes": ["cliente_id"],
    "fabricante_mensal": ["revenda_id", "mes", "canal"],
    # Crédito
    "credito_clientes": ["cliente_id"],
    "credito_cobranca": ["titulo_id"],
    "credito_solicitacoes": ["solicitacao_id"],
    "credito_historico": ["cliente_id", "data_implantacao"],
    "credito_pedidos": ["pedido_id"],
    "credito_alteracao": ["cliente_id"],
}


def trocar_arquivo(temporario, destino, tentativas=5):
    """os.replace com novas tentativas: no Windows o destino aberto por um leitor recusa a troca."""
    for tentativa in range(tentativas):
        try:
            os.replace(temporario, destino)
            return
        except PermissionError:
            if tentativa == tentativas - 1:
                raise
            time.sleep(0.25)


def gravar_parquet(df, destino):
    if df.empty:
        raise ValueError(f"{destino.name}: resultado vazio; o arquivo anterior foi mantido.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(f".{destino.stem}.{os.getpid()}.tmp")
    df.to_parquet(temporario, index=False)
    trocar_arquivo(temporario, destino)


def hash_conteudo(df):
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def publicar():
    manifesto = {"data_referencia": config.DATA_REFERENCIA.isoformat(), "marts": {}}
    # Sem read_only: o dbt roda no mesmo processo e o DuckDB recusa conexões com configuração diferente.
    with duckdb.connect(str(config.BANCO)) as con:
        for mart, grao in MARTS.items():
            df = con.execute(f"SELECT * FROM marts.{mart} ORDER BY {', '.join(grao)}").df()
            gravar_parquet(df, config.PASTA_PUBLICADO / f"{mart}.parquet")
            manifesto["marts"][mart] = {"linhas": len(df), "hash": hash_conteudo(df)}
            log.info("publicado %-34s %8d linhas", f"{mart}.parquet", len(df))

    temporario = config.PASTA_PUBLICADO / ".manifesto.tmp"
    temporario.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")
    trocar_arquivo(temporario, config.PASTA_PUBLICADO / "_manifesto.json")
    return manifesto
