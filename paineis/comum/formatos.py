"""Números e datas no formato brasileiro, para cards e tabelas montadas em Python."""
import pandas as pd

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def vazio(valor):
    """None, NaN, NaT e pd.NA."""
    return valor is None or (not isinstance(valor, str) and bool(pd.isna(valor)))


def numero(valor, casas=0):
    if vazio(valor):
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(valor, casas=2):
    if vazio(valor):
        return "—"
    return f"{'-' if valor < 0 else ''}R$ {numero(abs(valor), casas)}"


def moeda_curta(valor):
    """R$ 1,2 mi / -R$ 350,4 mil: para cards."""
    if vazio(valor):
        return "—"
    sinal, valor = ("-" if valor < 0 else ""), abs(valor)
    if valor >= 1_000_000:
        return f"{sinal}R$ {numero(valor / 1_000_000, 2)} mi"
    if valor >= 1_000:
        return f"{sinal}R$ {numero(valor / 1_000, 1)} mil"
    return f"{sinal}R$ {numero(valor, 2)}"


def pct(valor, casas=1):
    return "—" if vazio(valor) else f"{numero(valor, casas)}%"


def data(valor):
    return "—" if vazio(valor) or valor is None else valor.strftime("%d/%m/%Y")


def mes_rotulo(aaaamm):
    """202611 -> 'nov/26'."""
    return f"{MESES[aaaamm % 100 - 1]}/{str(aaaamm // 100)[2:]}"
