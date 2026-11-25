"""Snapshot diário do Estoque e Reposição: guarda a posição do dia como o painel a mostra.

Grava em dois lugares:
- data/snapshots/estoque_reposicao/<AAAA-MM-DD>.parquet (o que o modal do painel lê);
- tabela snapshots.estoque_reposicao_diario no DuckDB, chave (data_snapshot, revenda_id,
  produto_id, periodo, base_estoque).

É idempotente: rodar de novo no mesmo dia apaga o dia e grava outra vez, numa transação.
"""
import logging

import duckdb
import pandas as pd

from elt import config
from elt.publicar import gravar_parquet

log = logging.getLogger(__name__)


def gravar_snapshot(data=None):
    data = data or config.DATA_REFERENCIA
    df = pd.read_parquet(config.PASTA_PUBLICADO / "estoque_reposicao.parquet")
    df.insert(0, "data_snapshot", pd.Timestamp(data).date())

    gravar_parquet(df, config.PASTA_SNAPSHOTS / "estoque_reposicao" / f"{data.isoformat()}.parquet")

    with duckdb.connect(str(config.BANCO)) as con:
        con.register("snapshot", df)
        con.execute("CREATE SCHEMA IF NOT EXISTS snapshots")
        con.execute("CREATE TABLE IF NOT EXISTS snapshots.estoque_reposicao_diario AS SELECT * FROM snapshot LIMIT 0")
        con.execute("BEGIN")
        con.execute("DELETE FROM snapshots.estoque_reposicao_diario WHERE data_snapshot = ?", [data])
        con.execute("INSERT INTO snapshots.estoque_reposicao_diario SELECT * FROM snapshot")
        con.execute("COMMIT")
        total = con.execute("SELECT count(*) FROM snapshots.estoque_reposicao_diario WHERE data_snapshot = ?",
                            [data]).fetchone()[0]
    log.info("snapshot %s: %d linhas (parquet + snapshots.estoque_reposicao_diario)", data, total)
    return total
