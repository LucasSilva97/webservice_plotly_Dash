"""Contas das páginas do Comercial: pandas puro, sem Dash (testável sem servidor).

Regra geral: o que é aditivo (R$, caixas) vem somado dos marts; o que é contagem distinta
(clientes positivados) é contado aqui, depois dos filtros, a partir do mart por cliente.
"""
import pandas as pd

from paineis.comum import formatos
from paineis.comum.dados import ler_parquet

CANAIS = {"IMEDIATO": "Consumo imediato", "ABASTECIMENTO": "Abastecimento"}
COLUNA_META_CANAL = {"IMEDIATO": "meta_faturamento_imediato", "ABASTECIMENTO": "meta_faturamento_abastecimento"}
COLUNA_CAIXAS_CANAL = {"IMEDIATO": "meta_caixas_fabricante_imediato", "ABASTECIMENTO": "meta_caixas_fabricante_abastecimento"}
FABRICANTE_PROGRAMA = "Fábrica Horizonte"  # o mesmo da var fabricante_programa do dbt


def periodo_atual():
    periodos = ler_parquet("periodo_analise")
    return periodos[periodos["mes_atual"]].iloc[0]


def mes_anterior(mes):
    return mes - 89 if mes % 100 == 1 else mes - 1


def pct(parte, todo):
    return 100 * parte / todo if todo else None


# ------------------------------------------------------------------ metas
def meta(metas, revenda, mes, vendedores=None, canais=None, coluna_canal=COLUNA_META_CANAL):
    """Meta do recorte: soma dos vendedores escolhidos, ou a meta própria da revenda (vendedor 0)."""
    recorte = metas[(metas["revenda_id"] == revenda) & (metas["mes"] == mes)]
    recorte = recorte[recorte["vendedor_id"].isin(vendedores)] if vendedores else recorte[recorte["vendedor_id"] == 0]
    colunas = [coluna_canal[c] for c in (canais or coluna_canal)]
    return float(recorte[colunas].sum().sum())


def meta_clientes(metas, revenda, mes, vendedores=None):
    recorte = metas[(metas["revenda_id"] == revenda) & (metas["mes"] == mes)]
    recorte = recorte[recorte["vendedor_id"].isin(vendedores)] if vendedores else recorte[recorte["vendedor_id"] == 0]
    return float(recorte["meta_clientes_positivados"].sum())


# ------------------------------------------------------------------ diário de vendas
def filtrar_vendas(df, revenda, vendedores=None, canais=None, marcas=None):
    df = df[df["revenda_id"] == revenda]
    if vendedores:
        df = df[df["vendedor_id"].isin(vendedores)]
    if canais:
        df = df[df["canal"].isin(canais)]
    if marcas:
        df = df[df["marca"].isin(marcas)]
    return df


def positivados(positivacao, revenda, mes, vendedores=None, canais=None):
    """Clientes distintos com faturamento líquido > 0 no recorte."""
    p = positivacao[(positivacao["revenda_id"] == revenda) & (positivacao["mes"] == mes)]
    if vendedores:
        p = p[p["vendedor_id"].isin(vendedores)]
    if canais:
        p = p[p["canal"].isin(canais)]
    por_cliente = p.groupby("cliente_id")["valor_liquido"].sum()
    return int((por_cliente > 0).sum())


def diario(revenda, vendedores=None, canais=None, marcas=None):
    per = periodo_atual()
    mes, ref = int(per["mes"]), pd.Timestamp(per["data_referencia"])
    decorridos, uteis = int(per["dias_uteis_decorridos"]), int(per["dias_uteis_mes"])
    vendas = filtrar_vendas(ler_parquet("vendas_diarias"), revenda, vendedores, canais, marcas)
    vendas["data"] = pd.to_datetime(vendas["data"])
    metas = ler_parquet("metas_mes")
    positivacao = ler_parquet("positivacao_cliente_mes")

    atual = vendas[vendas["mes"] == mes]
    anterior = vendas[vendas["mes"] == mes_anterior(mes)]
    ano_anterior = vendas[(vendas["mes"] == mes - 100) & (vendas["data"].dt.day <= ref.day)]

    realizado = atual["valor_liquido"].sum()
    tendencia = realizado / decorridos * uteis if decorridos else 0.0
    valor_meta = meta(metas, revenda, mes, vendedores, canais)
    clientes = positivados(positivacao, revenda, mes, vendedores, canais)
    alvo_clientes = meta_clientes(metas, revenda, mes, vendedores)

    kpis = {
        "mes": mes, "data_referencia": ref.date(), "dias_uteis_decorridos": decorridos, "dias_uteis_mes": uteis,
        "realizado": realizado, "tendencia": tendencia, "meta": valor_meta,
        "ating_tendencia": pct(tendencia, valor_meta),
        "mes_anterior": anterior["valor_liquido"].sum(),
        "var_mes_anterior": pct(tendencia - anterior["valor_liquido"].sum(), anterior["valor_liquido"].sum()),
        "ano_anterior_ate_data": ano_anterior["valor_liquido"].sum(),
        "var_ano_anterior": pct(realizado - ano_anterior["valor_liquido"].sum(), ano_anterior["valor_liquido"].sum()),
        "caixas": atual["caixas_liquidas"].sum(),
        "mix": int(atual.loc[atual["valor_liquido"] > 0, "produto_id"].nunique()),
        "positivados": clientes, "meta_clientes": alvo_clientes, "ating_clientes": pct(clientes, alvo_clientes),
    }

    por_dia = atual.groupby("data", as_index=False)["valor_liquido"].sum().sort_values("data")
    por_dia["dia_util"] = range(1, len(por_dia) + 1)
    por_dia["acumulado"] = por_dia["valor_liquido"].cumsum()
    por_marca = (atual.groupby("marca")["valor_liquido"].sum().rename("atual").to_frame()
                 .join(ano_anterior.groupby("marca")["valor_liquido"].sum().rename("ano_anterior"), how="outer")
                 .fillna(0).sort_values("atual").reset_index())

    linhas = []
    nomes = metas[(metas["revenda_id"] == revenda) & (metas["vendedor_id"] != 0)][["vendedor_id", "vendedor"]].drop_duplicates()
    for v in nomes.sort_values("vendedor_id").itertuples():
        if vendedores and v.vendedor_id not in vendedores:
            continue
        do_vendedor = atual[atual["vendedor_id"] == v.vendedor_id]
        real_v = do_vendedor["valor_liquido"].sum()
        tend_v = real_v / decorridos * uteis if decorridos else 0.0
        meta_v = meta(metas, revenda, mes, [v.vendedor_id], canais)
        cli_v = positivados(positivacao, revenda, mes, [v.vendedor_id], canais)
        meta_cli_v = meta_clientes(metas, revenda, mes, [v.vendedor_id])
        linhas.append({"vendedor": v.vendedor, "realizado": real_v, "tendencia": tend_v, "meta": meta_v,
                       "ating": pct(tend_v, meta_v), "caixas": do_vendedor["caixas_liquidas"].sum(),
                       "positivados": cli_v, "meta_clientes": meta_cli_v, "ating_clientes": pct(cli_v, meta_cli_v)})
    return kpis, por_dia, por_marca, pd.DataFrame(linhas)


# ------------------------------------------------------------------ metas do mês
def metas_do_mes(revenda, mes):
    per = ler_parquet("periodo_analise").set_index("mes").loc[mes]
    decorridos, uteis = int(per["dias_uteis_decorridos"]), int(per["dias_uteis_mes"])
    metas = ler_parquet("metas_mes")
    metas = metas[(metas["revenda_id"] == revenda) & (metas["mes"] == mes)]
    vendas = ler_parquet("vendas_diarias")
    vendas = vendas[(vendas["revenda_id"] == revenda) & (vendas["mes"] == mes)]
    positivacao = ler_parquet("positivacao_cliente_mes")

    def linha(nome, recorte_meta, recorte_vendas, vendedores):
        realizado = recorte_vendas["valor_liquido"].sum()
        tendencia = realizado / decorridos * uteis if 0 < decorridos < uteis else realizado
        caixas = recorte_vendas.loc[recorte_vendas["fabricante"] == FABRICANTE_PROGRAMA, "caixas_liquidas"].sum()
        meta_rs = recorte_meta["meta_faturamento_total"].sum()
        meta_cx = recorte_meta[["meta_caixas_fabricante_imediato", "meta_caixas_fabricante_abastecimento"]].sum().sum()
        meta_cli = recorte_meta["meta_clientes_positivados"].sum()
        clientes = positivados(positivacao, revenda, mes, vendedores)
        return {"vendedor": nome, "meta": meta_rs, "realizado": realizado, "tendencia": tendencia,
                "ating": pct(tendencia, meta_rs), "meta_caixas": meta_cx, "caixas": caixas,
                "ating_caixas": pct(caixas, meta_cx), "meta_clientes": meta_cli, "positivados": clientes,
                "ating_clientes": pct(clientes, meta_cli)}

    linhas = [linha(m.vendedor, metas[metas["vendedor_id"] == m.vendedor_id],
                    vendas[vendas["vendedor_id"] == m.vendedor_id], [m.vendedor_id])
              for m in metas[metas["vendedor_id"] != 0].sort_values("vendedor_id").itertuples()]
    total = linha("Revenda (meta própria)", metas[metas["vendedor_id"] == 0], vendas, None)
    return pd.DataFrame(linhas), total, {"decorridos": decorridos, "uteis": uteis}


# ------------------------------------------------------------------ carteira de clientes
EQUIPAMENTOS = {"Geladeira vertical": "geladeira_vertical", "Freezer horizontal": "freezer_horizontal",
                "Carrinho térmico": "carrinho_termico"}
FILTROS_CARTEIRA = {
    "vendedor_id": "Vendedor", "canal": "Canal", "cidade": "Cidade", "bairro": "Bairro",
    "status_inadimplencia": "Inadimplência", "faixa_atraso": "Tempo de atraso",
    "equipamento": "Equipamento cedido", "faixa_m0": "Compra no mês", "cliente_id": "Cliente",
}
ORDEM_ATRASO = ["Sem títulos", "A vencer", "1 semana"] + [f"{n} semanas" for n in range(2, 8)] + ["8+ semanas"]
ORDEM_FAIXA = ["Sem compra", "Até R$ 300", "R$ 300 a 800", "R$ 800 a 2.000", "Acima de R$ 2.000"]


def aplicar_carteira(df, valores, excluir=None):
    """Aplica os filtros da carteira; `excluir` deixa um de fora (para montar as opções cruzadas)."""
    for campo, escolhidos in valores.items():
        if campo == excluir or not escolhidos:
            continue
        if campo == "equipamento":
            mascara = pd.Series(False, index=df.index)
            for nome in escolhidos:
                mascara |= (df["equipamentos_total"] == 0) if nome == "Sem equipamento" else (df[EQUIPAMENTOS[nome]] > 0)
            df = df[mascara]
        else:
            df = df[df[campo].isin(escolhidos)]
    return df


def opcoes_carteira(df, campo):
    if campo == "equipamento":
        return [{"label": n, "value": n} for n in list(EQUIPAMENTOS) + ["Sem equipamento"]]
    if campo == "cliente_id":
        clientes = df[["cliente_id", "fantasia"]].drop_duplicates().sort_values("fantasia")
        return [{"label": f"{c.cliente_id} – {c.fantasia}", "value": c.cliente_id} for c in clientes.itertuples()]
    valores = df[campo].dropna().unique().tolist()
    ordem = {"faixa_atraso": ORDEM_ATRASO, "faixa_m0": ORDEM_FAIXA}.get(campo)
    valores = sorted(valores, key=ordem.index) if ordem else sorted(valores)
    return [{"label": str(v), "value": v} for v in valores]


def carteira(revenda, situacao, classe, valores):
    df = ler_parquet("base_clientes")
    df = df[(df["revenda_id"] == revenda) & (df["situacao"] == situacao)]
    if classe and classe != "Todos":
        df = df[df["classe"] == classe]
    filtrado = aplicar_carteira(df, valores)
    opcoes = {campo: opcoes_carteira(aplicar_carteira(df, valores, excluir=campo), campo) for campo in FILTROS_CARTEIRA}
    return filtrado.sort_values("valor_vencido", ascending=False), opcoes


def rotulos_meses():
    """Títulos das 5 colunas de faturamento: m4 ... m0 (mês corrente)."""
    mes = int(periodo_atual()["mes"])
    rotulos, m = {}, mes
    for k in range(5):
        rotulos[f"fat_m{k}"] = formatos.mes_rotulo(m)
        m = mes_anterior(m)
    return rotulos


# ------------------------------------------------------------------ ruptura
def ruptura(revenda, mes, vendedor=None):
    df = ler_parquet("ruptura_vendedor_mes")
    df = df[df["revenda_id"] == revenda]
    escopo = df[df["vendedor_id"] == vendedor] if vendedor else df
    contas = ["clientes_ativos", "clientes_cobertos", "clientes_sem_compra", "clientes_inadimplentes",
              "clientes_novos", "clientes_cancelados", "captacao_liquida"]
    evolucao = escopo.groupby("mes", as_index=False)[contas].sum()
    evolucao["perc_cobertura"] = 100 * evolucao["clientes_cobertos"] / evolucao["clientes_ativos"]
    evolucao["perc_ruptura"] = 100 - evolucao["perc_cobertura"]

    do_mes = df[df["mes"] == mes].copy()
    if vendedor:
        do_mes = do_mes[do_mes["vendedor_id"] == vendedor]
    total = do_mes[contas].sum()
    total = {**total.to_dict(), "vendedor": "TOTAL",
             "perc_cobertura": pct(total["clientes_cobertos"], total["clientes_ativos"]),
             "perc_ruptura": pct(total["clientes_sem_compra"], total["clientes_ativos"]),
             "perc_inadimplencia": pct(total["clientes_inadimplentes"], total["clientes_ativos"])}
    anterior = evolucao[evolucao["mes"] == mes_anterior(mes)]
    variacao = None
    if len(anterior) and total["perc_cobertura"] is not None:
        variacao = total["perc_cobertura"] - float(anterior["perc_cobertura"].iloc[0])
    return do_mes.sort_values("vendedor_id"), total, evolucao, variacao


# ------------------------------------------------------------------ painel do fabricante
MESES_ROTULO = formatos.MESES


def fabricante(revenda, canal):
    """Tabelas ano x mês de caixas, clientes com compra e ruptura (ano corrente x anterior)."""
    df = ler_parquet("fabricante_mensal")
    ano = int(periodo_atual()["mes"]) // 100
    df = df[(df["revenda_id"] == revenda) & (df["canal"] == canal)]
    atual = df[df["ano"] == ano].set_index("mes_calendario").reindex(range(1, 13))
    anterior = df[df["ano"] == ano - 1].set_index("mes_calendario").reindex(range(1, 13))
    meses_com_dado = atual["caixas_fabricante"].notna()
    ultimo = int(atual.index[meses_com_dado].max()) if meses_com_dado.any() else 0

    def crescimento(a, b):
        return [pct(x - y, y) if pd.notna(x) and pd.notna(y) else None for x, y in zip(a, b)]

    caixas = {
        "atual": atual["caixas_fabricante"].tolist(), "anterior": anterior["caixas_fabricante"].tolist(),
        "meta": atual["meta_caixas"].tolist(),
        "total_atual": atual["caixas_fabricante"].sum(),
        "total_anterior": anterior.loc[:ultimo, "caixas_fabricante"].sum(),
        "total_meta": atual.loc[:ultimo, "meta_caixas"].sum(),
    }
    caixas["crescimento"] = crescimento(caixas["atual"], caixas["anterior"])
    caixas["atingimento"] = [pct(a, m) if pd.notna(a) and pd.notna(m) else None for a, m in zip(caixas["atual"], caixas["meta"])]

    clientes = {
        "atual": atual["clientes_com_compra"].tolist(), "anterior": anterior["clientes_com_compra"].tolist(),
        "meta": atual["meta_clientes"].tolist(),
        "total_atual": atual.loc[ultimo, "clientes_acumulados_ano"] if ultimo else None,
        "total_anterior": anterior.loc[ultimo, "clientes_acumulados_ano"] if ultimo else None,
    }
    clientes["crescimento"] = crescimento(clientes["atual"], clientes["anterior"])
    clientes["atingimento"] = [pct(a, m) if pd.notna(a) and pd.notna(m) else None for a, m in zip(clientes["atual"], clientes["meta"])]

    ruptura_ = {
        "atual": atual["perc_ruptura"].tolist(), "anterior": anterior["perc_ruptura"].tolist(),
        "meta": atual["meta_ruptura"].tolist(),
    }
    ruptura_["melhoria"] = [y - x if pd.notna(x) and pd.notna(y) else None for x, y in zip(ruptura_["atual"], ruptura_["anterior"])]
    return {"ano": ano, "ultimo_mes": ultimo, "caixas": caixas, "clientes": clientes, "ruptura": ruptura_}
