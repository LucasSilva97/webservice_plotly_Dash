"""Contas do painel de Estoque e Reposição: pandas puro, sem Dash (testável sem servidor).

As regras (mínimo, máximo, puxar/reduzir, dias de estoque) já vêm calculadas no mart
estoque_reposicao; aqui só se filtra e se soma para os cards.
"""
import pandas as pd

from paineis.comum.dados import PASTA_SNAPSHOTS, ler_parquet

PERIODOS = {"MES_ATUAL": "Mês atual", "MES_ANTERIOR": "Mês anterior", "ULTIMOS_30_DIAS": "Últimos 30 dias"}
BASES = {"SISTEMA": "Saldo do sistema", "CONTAGEM": "Última contagem"}
ACOES = {"TODOS": "Todos", "PUXAR": "Só puxar", "REDUZIR": "Só reduzir"}
MARCA_PRINCIPAL = "Horizonte"
FAIXA_DDE = (8, 14)  # a mesma faixa das vars dias_estoque_minimo/maximo do dbt
PASTA_SNAPSHOT = PASTA_SNAPSHOTS / "estoque_reposicao"


def carregar():
    estoque = ler_parquet("estoque_reposicao")
    recebidas = ler_parquet("estoque_transferencias_recebidas")
    contagem = recebidas.groupby(["revenda_id", "produto_id"]).size().rename("transf_apos_compra").reset_index()
    estoque = estoque.merge(contagem, on=["revenda_id", "produto_id"], how="left")
    estoque["transf_apos_compra"] = estoque["transf_apos_compra"].fillna(0).astype(int)
    return estoque


def filtrar(df, revenda, periodo, base, marcas=None, categorias=None, produtos=None, acao="TODOS"):
    df = df[(df["revenda_id"] == revenda) & (df["periodo"] == periodo) & (df["base_estoque"] == base)]
    if marcas:
        df = df[df["marca"].isin(marcas)]
    if categorias:
        df = df[df["categoria"].isin(categorias)]
    if produtos:
        df = df[df["produto_id"].isin(produtos)]
    if acao == "PUXAR":
        df = df[df["reduzir_puxar"] > 0]
    elif acao == "REDUZIR":
        df = df[df["reduzir_puxar"] < 0]
    return df.sort_values("analise_rs")


def dias_de_estoque(df):
    """Dias úteis de estoque ponderados pelo volume: HL em estoque / HL vendido por dia útil."""
    media = df["media_hl_dia"].sum()
    return df["hl_estoque"].sum() / media if media else None


def sellin_sellout(df, sellin):
    """% de compra da fábrica sobre a venda (em HL), nos meses do período e nos produtos da tela."""
    if df.empty:
        return None, 0.0, 0.0
    linha = df.iloc[0]
    recorte = sellin[(sellin["revenda_id"] == linha["revenda_id"])
                     & sellin["mes"].between(linha["mes_inicio"], linha["mes_fim"])
                     & sellin["produto_id"].isin(df["produto_id"])]
    comprado, vendido = recorte["hl_comprado"].sum(), recorte["hl_vendido"].sum()
    return (100 * comprado / vendido if vendido else None), comprado, vendido


def indicadores(df, sellin=None):
    estoque = df["estoque_valorizado"].sum()
    puxada = df.loc[df["analise_rs"] > 0, "analise_rs"].sum()
    reduzir = df.loc[df["analise_rs"] < 0, "analise_rs"].sum()
    resultado = {
        "estoque_rs": estoque,
        "estoque_hl": df["hl_estoque"].sum(),
        "puxada_rs": puxada,
        "puxada_pct": 100 * puxada / estoque if estoque else None,
        "reduzir_rs": reduzir,
        "reduzir_pct": 100 * abs(reduzir) / estoque if estoque else None,
        "produtos_ruptura": int(df["em_ruptura"].sum()),
        "dde_geral": dias_de_estoque(df),
        "dde_marca": dias_de_estoque(df[df["marca"] == MARCA_PRINCIPAL]),
        "media_hl_dia": df["media_hl_dia"].sum(),
    }
    if sellin is not None:
        resultado["sellin_pct"], resultado["hl_comprado"], resultado["hl_vendido"] = sellin_sellout(df, sellin)
    return resultado


def detalhe_produto(revenda, produto):
    """Notas em trânsito e transferências recebidas depois da última compra, de um produto."""
    notas = ler_parquet("estoque_transito_notas")
    recebidas = ler_parquet("estoque_transferencias_recebidas")
    notas = notas[(notas["revenda_id"] == revenda) & (notas["produto_id"] == produto)]
    recebidas = recebidas[(recebidas["revenda_id"] == revenda) & (recebidas["produto_id"] == produto)]
    return notas.sort_values("data_emissao"), recebidas.sort_values("data_entrada")


def datas_snapshot():
    return sorted((p.stem for p in PASTA_SNAPSHOT.glob("*.parquet")), reverse=True)


def carregar_snapshot(data):
    return pd.read_parquet(PASTA_SNAPSHOT / f"{data}.parquet").assign(transf_apos_compra=0)
