"""Porta de entrada dos dados dos painéis: só leitura de Parquet, nunca o banco.

O contrato com o pipeline é a pasta data/publicado/ e o nome de cada arquivo. As duas metades
do projeto (elt/ e paineis/) não importam código uma da outra.
"""
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PASTA_PUBLICADO = RAIZ / "data" / "publicado"
PASTA_SNAPSHOTS = RAIZ / "data" / "snapshots"
ERP_LOCAL = RAIZ / "data" / "fontes" / "erp.sqlite"   # só o Crédito grava aqui (solicitações)


def ler_parquet(nome, tentativas=4):
    """Lê o arquivo publicado; repete se ele estiver sendo trocado pelo pipeline naquele instante."""
    caminho = PASTA_PUBLICADO / f"{nome}.parquet"
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho.name} não encontrado. Rode o ELT antes: python -m elt")
    for tentativa in range(tentativas):
        try:
            return pd.read_parquet(caminho)
        except OSError:
            if tentativa == tentativas - 1:
                raise
            time.sleep(0.25)


def data_geracao(nome):
    """Quando o arquivo foi publicado (mtime)."""
    caminho = PASTA_PUBLICADO / f"{nome}.parquet"
    return datetime.fromtimestamp(caminho.stat().st_mtime) if caminho.exists() else None


def data_referencia():
    """A data de referência do último ELT (o "hoje" da demonstração), lida do manifesto."""
    manifesto = PASTA_PUBLICADO / "_manifesto.json"
    if not manifesto.exists():
        return None
    return datetime.fromisoformat(json.loads(manifesto.read_text(encoding="utf-8"))["data_referencia"]).date()


def opcoes(serie, rotulos=None):
    """Opções de dropdown a partir dos valores de uma coluna, ordenadas."""
    valores = sorted(v for v in serie.dropna().unique())
    return [{"label": (rotulos or {}).get(v, str(v)), "value": v} for v in valores]


def para_grade(df):
    """Linhas para o AG Grid: datas viram texto ISO e NaN vira nulo."""
    saida = df.copy()
    for coluna in saida.columns:
        amostra = saida[coluna].dropna()
        if len(amostra) and hasattr(amostra.iloc[0], "isoformat"):  # date, datetime ou Timestamp
            saida[coluna] = saida[coluna].map(lambda d: d.isoformat()[:10] if pd.notna(d) else None)
    return saida.astype(object).where(saida.notna(), None).to_dict("records")
