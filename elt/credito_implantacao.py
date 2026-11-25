"""Implantação mensal de limite e prazo, gravando SÓ no ERP local da demonstração.

    python -m elt.credito_implantacao                      simula: mostra o que mudaria e não grava
    python -m elt.credito_implantacao --executar           grava em data/fontes/erp.sqlite
    python -m elt.credito_implantacao --revendas 20,30     só essas revendas
    python -m elt.credito_implantacao --executar --repetir refaz uma implantação já gravada

Entrada: data/publicado/credito_alteracao.parquet (a proposta calculada pelo dbt).
Por revenda, numa transação: INSERT no histórico de implantações + UPDATE do limite e da
condição de pagamento de cada cliente. Se um UPDATE não afetar exatamente 1 linha, a revenda
inteira é desfeita. Trava: revenda que já tem implantação nessa data é pulada.
Depois de executar, `python -m elt --manter-fontes` leva o efeito aos painéis.
"""
import argparse
import sqlite3
from contextlib import closing

import pandas as pd

from elt import config

INSERT_HISTORICO = """
    INSERT INTO historico_implantacoes (revenda_id, cliente_id, data_implantacao, classificacao,
        prazo_dias_antes, prazo_dias_depois, media_atraso, faturamento_medio, limite_antes, limite_depois)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
UPDATE_CLIENTE = """
    UPDATE clientes SET limite_credito = ?, condicao_pagamento_id = ?
    WHERE cliente_id = ? AND revenda_id = ?"""


def implantar(executar=False, revendas=None, repetir=False):
    proposta = pd.read_parquet(config.PASTA_PUBLICADO / "credito_alteracao.parquet")
    if revendas:
        proposta = proposta[proposta["revenda_id"].isin(revendas)]
    resumo = []
    with closing(sqlite3.connect(config.ERP)) as con:
        for revenda_id, linhas in proposta.groupby("revenda_id"):
            data = pd.Timestamp(linhas["data_implantacao"].iloc[0]).date().isoformat()
            ja_feita = con.execute("SELECT count(*) FROM historico_implantacoes WHERE revenda_id = ? AND data_implantacao = ?",
                                   (int(revenda_id), data)).fetchone()[0]
            if ja_feita and not repetir:
                resumo.append((revenda_id, data, "já implantada (use --repetir)", 0))
                continue
            if not executar:
                resumo.append((revenda_id, data, "simulada, nada gravado", len(linhas)))
                continue
            try:
                with con:  # transação do sqlite3: commit no fim, rollback se der erro
                    con.execute("DELETE FROM historico_implantacoes WHERE revenda_id = ? AND data_implantacao = ?",
                                (int(revenda_id), data))
                    for l in linhas.itertuples(index=False):
                        con.execute(INSERT_HISTORICO, (
                            int(l.revenda_id), int(l.cliente_id), data, l.classificacao,
                            int(l.prazo_atual_dias), int(l.prazo_novo_dias), float(l.media_atraso),
                            float(l.faturamento_medio_3m), float(l.limite_atual), float(l.limite_novo)))
                        cursor = con.execute(UPDATE_CLIENTE, (float(l.limite_novo), int(l.condicao_nova_id),
                                                              int(l.cliente_id), int(l.revenda_id)))
                        if cursor.rowcount != 1:
                            raise RuntimeError(f"cliente {l.cliente_id}: UPDATE afetou {cursor.rowcount} linhas")
                resumo.append((revenda_id, data, "implantada", len(linhas)))
            except Exception as erro:
                resumo.append((revenda_id, data, f"desfeita: {erro}", 0))
    return pd.DataFrame(resumo, columns=["revenda_id", "data_implantacao", "situacao", "clientes"])


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m elt.credito_implantacao")
    parser.add_argument("--executar", action="store_true", help="grava no ERP local (sem ele, só simula)")
    parser.add_argument("--revendas", help="lista separada por vírgula, ex.: 20,30")
    parser.add_argument("--repetir", action="store_true", help="refaz a implantação já gravada na data")
    args = parser.parse_args(argv)
    revendas = [int(r) for r in args.revendas.split(",")] if args.revendas else None
    print(implantar(args.executar, revendas, args.repetir).to_string(index=False))


if __name__ == "__main__":
    main()
