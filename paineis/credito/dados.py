"""Consulta das páginas do Crédito e Prazo: pandas puro sobre a declaração de cada página."""
import pandas as pd

from paineis.comum.dados import ler_parquet

ROTULOS_BOOL = {True: "Sim", False: "Não"}


def carregar(pagina, revenda, seletor=None):
    df = ler_parquet(pagina.parquet)
    df = df[df["revenda_id"] == revenda]
    if pagina.seletor and seletor:
        df = df[pd.to_datetime(df[pagina.seletor]).dt.strftime("%Y-%m-%d") == seletor]
    return df


def opcoes_seletor(pagina):
    """Datas de implantação, da mais nova para a mais antiga (valor em texto ISO)."""
    datas = pd.to_datetime(ler_parquet(pagina.parquet)[pagina.seletor]).drop_duplicates().sort_values(ascending=False)
    return [{"label": d.strftime("%d/%m/%Y"), "value": d.strftime("%Y-%m-%d")} for d in datas]


def aplicar(df, pagina, clientes, valores):
    """valores: {campo: [escolhidos]}. Coluna numérica compara pelo número; bool pelo Sim/Não."""
    if clientes:
        df = df[df["cliente_id"].isin(clientes)]
    for campo, escolhidos in valores.items():
        if escolhidos:
            df = df[df[campo].isin(escolhidos)]
    campo, crescente = pagina.ordem
    return df.sort_values(campo, ascending=crescente, kind="stable", na_position="last")


def opcoes_filtro(df, campo):
    valores = df[campo].dropna().unique().tolist()
    if df[campo].dtype == bool:
        return [{"label": ROTULOS_BOOL[v], "value": v} for v in sorted(valores, reverse=True)]
    if campo in ("prazo_atual", "novo_prazo", "prazo_depois"):
        return [{"label": v, "value": v} for v in sorted(valores, key=lambda t: 0 if t == "À vista" else int(t.split()[0]))]
    if campo == "sugestao_limite":
        return [{"label": v, "value": v} for v in sorted(valores, key=lambda t: 0 if t == "À vista" else int(t[3:].replace(".", "")))]
    return [{"label": str(v), "value": v} for v in sorted(valores)]


def opcoes_cliente(df):
    nome = "fantasia" if "fantasia" in df.columns else "razao_social"
    clientes = df[["cliente_id", nome]].drop_duplicates("cliente_id").sort_values(nome)
    return [{"label": f"{r.cliente_id} – {getattr(r, nome)}", "value": r.cliente_id} for r in clientes.itertuples()]


def pedidos_do_cliente(cliente_id):
    pedidos = ler_parquet("credito_pedidos")
    pedidos = pedidos[pedidos["cliente_id"] == cliente_id].sort_values("data_emissao", ascending=False)
    pagos = pedidos[pedidos["situacao"] == "Pago"]
    resumo = {
        "pedidos": len(pedidos),
        "valor": pedidos.loc[pedidos["status"] == "FATURADO", "valor_total"].sum(),
        "media_atraso": pagos["dias_atraso"].mean() if len(pagos) else None,
        "vencidos": int((pedidos["situacao"] == "Vencido").sum()),
    }
    return pedidos, resumo


def proxima_implantacao():
    alteracao = ler_parquet("credito_alteracao")
    return pd.Timestamp(alteracao["data_implantacao"].iloc[0]).date() if len(alteracao) else None
