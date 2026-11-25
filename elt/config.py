"""Configuração única do pipeline: caminhos, semente e data de referência.

A data de referência é fixa de propósito. Com a mesma semente e a mesma data, o gerador
produz as mesmas fontes e o ELT produz os mesmos marts, em qualquer dia em que rodar.
"""
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Fontes fictícias (o "sistema de origem" da demonstração)
PASTA_FONTES = RAIZ / "data" / "fontes"
ERP = PASTA_FONTES / "erp.sqlite"
PASTA_PLANILHAS = PASTA_FONTES / "planilhas"

# Armazém analítico (DuckDB) e projeto dbt
BANCO = RAIZ / "data" / "warehouse" / "distribuidora.duckdb"
PROJETO_DBT = RAIZ / "transform"

# Publicação consumida pelos painéis
PASTA_PUBLICADO = RAIZ / "data" / "publicado"
PASTA_SNAPSHOTS = RAIZ / "data" / "snapshots"
PASTA_LOGS = RAIZ / "logs"

SEMENTE = 20261118
DATA_REFERENCIA = date(2026, 11, 18)   # "hoje" da demonstração (quarta-feira)
INICIO_HISTORICO = date(2025, 1, 1)    # primeiro dia com vendas nas fontes

# Carga incremental das vendas: só os últimos N meses são apagados e recarregados.
JANELA_VENDAS_MESES = 3
