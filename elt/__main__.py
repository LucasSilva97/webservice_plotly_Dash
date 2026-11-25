"""ELT completo da demonstração.

    python -m elt                    gera as fontes, carrega a raw (completa), roda o dbt, publica e grava o snapshot
    python -m elt --manter-fontes    não regenera as fontes (mantém o que os painéis gravaram nelas);
                                     pedidos e itens entram pela carga por janela (últimos meses)
    python -m elt --manter-fontes --completo   idem, mas recarregando o histórico inteiro

Etapas, na ordem:
  1. gerar fontes      elt/gerar_fontes.py   -> data/fontes/ (ERP em SQLite + planilha CSV)
  2. extrair e carregar elt/ingestao.py      -> schema raw do DuckDB
  3. transformar       dbt build (seeds, staging, intermediate, marts e testes)
  4. publicar          elt/publicar.py       -> data/publicado/*.parquet + _manifesto.json
  5. snapshot          elt/snapshot_estoque.py -> data/snapshots/ + snapshots.estoque_reposicao_diario
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

from elt import config, gerar_fontes, ingestao, publicar, snapshot_estoque

log = logging.getLogger("elt")


def configurar_log():
    config.PASTA_LOGS.mkdir(exist_ok=True)
    arquivo = config.PASTA_LOGS / f"elt_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(arquivo, encoding="utf-8")])


def rodar_dbt(*argumentos):
    from dbt.cli.main import dbtRunner  # importado aqui: o dbt demora para carregar

    os.environ["DBT_DUCKDB_PATH"] = str(config.BANCO)
    variaveis = json.dumps({"data_referencia": config.DATA_REFERENCIA.isoformat()})
    resultado = dbtRunner().invoke([
        *argumentos,
        "--project-dir", str(config.PROJETO_DBT),
        "--profiles-dir", str(config.PROJETO_DBT),
        "--vars", variaveis,
    ])
    if not resultado.success:
        raise RuntimeError(f"dbt {' '.join(argumentos)} falhou; veja a saída acima.")


def etapa(nome, funcao, *args, **kwargs):
    inicio = time.perf_counter()
    log.info("== %s", nome)
    retorno = funcao(*args, **kwargs)
    log.info("== %s: ok em %.1f s", nome, time.perf_counter() - inicio)
    return retorno


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m elt", description="ELT completo da demonstração")
    parser.add_argument("--manter-fontes", action="store_true", help="não regenera data/fontes/")
    parser.add_argument("--completo", action="store_true", help="recarrega o histórico inteiro das tabelas por janela")
    args = parser.parse_args(argv)

    configurar_log()
    log.info("data de referência %s, semente %s", config.DATA_REFERENCIA, config.SEMENTE)
    if not args.manter_fontes:
        etapa("1. gerar fontes", gerar_fontes.gerar)
    # Fonte recriada do zero é como um sistema de origem novo: o histórico é recarregado inteiro.
    # Sobre as mesmas fontes (--manter-fontes), pedidos e itens usam a carga por janela.
    etapa("2. extrair e carregar (raw)", ingestao.ingerir, completo=args.completo or not args.manter_fontes)
    etapa("3. transformar (dbt build)", rodar_dbt, "build")
    etapa("4. publicar parquet", publicar.publicar)
    etapa("5. snapshot do estoque", snapshot_estoque.gravar_snapshot)
    log.info("ELT concluído. Para abrir os painéis: python -m paineis")


if __name__ == "__main__":
    main()
