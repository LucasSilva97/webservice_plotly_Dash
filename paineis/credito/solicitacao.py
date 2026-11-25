"""Registro de solicitação de alteração de limite e prazo, no ERP LOCAL da demonstração.

É o adaptador que, na demonstração, faz o papel do portal de solicitações de crédito: grava em
data/fontes/erp.sqlite, tabela solicitacoes_credito, com origem 'painel' e situação 'Em análise'.
A solicitação aparece na aba Solicitações depois do próximo `python -m elt --manter-fontes`.
"""
import sqlite3
from contextlib import closing
from datetime import date

from paineis.comum.dados import ERP_LOCAL

PRAZOS_VALIDOS = (0, 7, 14, 21, 28)


def registrar(revenda_id, cliente_id, limite_atual, limite_solicitado, prazo_dias, solicitante, observacao):
    """Grava a solicitação e devolve o número dela. Erro de validação vira ValueError."""
    if not solicitante or not solicitante.strip():
        raise ValueError("Informe o solicitante.")
    if limite_solicitado is None and prazo_dias is None:
        raise ValueError("Escolha um novo limite, um novo prazo ou os dois.")
    if limite_solicitado is not None and limite_solicitado <= 0:
        raise ValueError("O limite pedido precisa ser maior que zero.")
    if prazo_dias is not None and prazo_dias not in PRAZOS_VALIDOS:
        raise ValueError("Prazo inválido.")
    tipo = "Limite e prazo" if limite_solicitado is not None and prazo_dias is not None else "Limite" if limite_solicitado is not None else "Prazo"
    if not ERP_LOCAL.exists():  # publicação online: só os Parquet vão para o servidor, o ERP fica na máquina
        raise ValueError("Esta publicação é só para consulta: as solicitações são gravadas no ERP local, "
                         "que existe quando o projeto roda na sua máquina (python -m elt).")

    with closing(sqlite3.connect(ERP_LOCAL)) as con, con:  # o segundo "con" abre a transação
        numero = con.execute("SELECT coalesce(max(solicitacao_id), 0) + 1 FROM solicitacoes_credito").fetchone()[0]
        con.execute(
            """INSERT INTO solicitacoes_credito (solicitacao_id, revenda_id, cliente_id, data_solicitacao, tipo,
                   limite_atual, limite_solicitado, prazo_solicitado_dias, situacao, solicitante, observacao, origem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Em análise', ?, ?, 'painel')""",
            (numero, revenda_id, cliente_id, date.today().isoformat(), tipo, limite_atual, limite_solicitado,
             prazo_dias, solicitante.strip(), (observacao or "").strip()))
    return numero
