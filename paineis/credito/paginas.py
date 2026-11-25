"""As quatro páginas do Crédito e Prazo declaradas como dados: parquet, colunas, filtros e cards.
Layout, callbacks e exportação são genéricos e leem esta declaração."""
from dataclasses import dataclass, field

from paineis.comum import componentes as c
from paineis.comum import formatos

VERMELHO = {"color": "#c0392b", "fontWeight": "700"}
VERDE = {"color": "#2e8b57", "fontWeight": "700"}
VINHO = {"color": "#7b1f3a", "fontWeight": "700"}
SINAL = {"styleConditions": [{"condition": "params.value < 0", "style": VERMELHO}, {"condition": "params.value > 0", "style": VERDE}]}
NEGATIVO = {"styleConditions": [{"condition": "params.value < 0", "style": VERMELHO}]}
POSITIVO_RUIM = {"styleConditions": [{"condition": "params.value > 0", "style": VERMELHO}]}
PRAZO_NOVO = {"styleConditions": [{"condition": "params.value", "style": VINHO}]}
SITUACAO = {"styleConditions": [
    {"condition": "params.value === 'Aprovada'", "style": VERDE},
    {"condition": "params.value === 'Reprovada'", "style": VERMELHO},
    {"condition": "params.value === 'Em análise'", "style": {"color": "#5d6d75", "fontStyle": "italic"}},
]}


@dataclass
class Pagina:
    slug: str
    titulo: str
    parquet: str
    chave: str                      # identifica a linha na grade
    colunas: list
    filtros: dict                   # campo -> rótulo
    cards: callable
    ordem: tuple                    # (campo, crescente?)
    seletor: str | None = None      # campo de escolha única que recorta a página inteira
    detalhe_cliente: bool = field(default=False)  # clique na linha mostra pedidos e a solicitação


def _cards_inicio(df):
    total = len(df)
    com_limite = int(((df["limite_atual"] > 0) & (df["prazo_dias"] > 0)).sum())
    comprometidos = df[df["limite_comprometido"]]
    return [
        c.card("Clientes", formatos.numero(total), f"{formatos.pct(100 * com_limite / total if total else None)} com limite e prazo", "escuro"),
        c.card("Limite comprometido", formatos.numero(len(comprometidos)),
               f"{formatos.moeda_curta(-comprometidos['saldo_limite'].sum())} acima do limite", "vermelho"),
        c.card("Vai para à vista", formatos.numero((df["novo_prazo_dias"] == 0).sum()), "débito antigo ou atraso alto", "vermelho"),
        c.card("Redução de prazo", formatos.numero(df["novo_prazo_dias"].isin([7, 14]).sum()), "média de atraso alta", "ambar"),
        c.card("Limite aumentado", formatos.numero(((df["alteracao_limite"] > 0) & (df["prazo_dias"] > 0)).sum()), "sugestão acima do atual", "verde"),
        c.card("Limite reduzido", formatos.numero(((df["alteracao_limite"] < 0) & (df["prazo_dias"] > 0)).sum()), "sugestão abaixo do atual", "ambar"),
    ]


def _cards_cobranca(df):
    vencidos = df[df["dias_atraso"] > 0]
    cards = [
        c.card("Clientes inadimplentes", formatos.numero(vencidos["cliente_id"].nunique()), f"{formatos.moeda_curta(vencidos['valor'].sum())} vencidos", "escuro"),
        c.card("A vencer", formatos.moeda_curta(df.loc[df["dias_atraso"] == 0, "valor"].sum()), f"{(df['dias_atraso'] == 0).sum()} títulos", "verde"),
    ]
    for rotulo, semanas in [("1 semana", [1]), ("2 semanas", [2]), ("3 a 4 semanas", [3, 4]), ("5 semanas ou mais", list(range(5, 100)))]:
        faixa = df[df["semanas_atraso"].isin(semanas)]
        cards.append(c.card(rotulo, formatos.moeda_curta(faixa["valor"].sum()), f"{faixa['cliente_id'].nunique()} clientes", "vermelho"))
    cards.append(c.card("Juros acumulados", formatos.moeda_curta(df["juros"].sum()), "juros simples por dia de atraso", "ambar"))
    return cards


def _cards_solicitacoes(df):
    return [
        c.card("Solicitações", formatos.numero(len(df)), f"{(df['origem'] == 'painel').sum()} registradas pelo painel", "escuro"),
        c.card("Em análise", formatos.numero((df["situacao"] == "Em análise").sum()), "aguardando o crédito", "ambar"),
        c.card("Aprovadas", formatos.numero((df["situacao"] == "Aprovada").sum()), "", "verde"),
        c.card("Reprovadas", formatos.numero((df["situacao"] == "Reprovada").sum()), "", "vermelho"),
    ]


def _cards_historico(df):
    return [
        c.card("Clientes na implantação", formatos.numero(len(df)), "", "escuro"),
        c.card("Aumentos de limite", formatos.numero((df["tipo_alteracao"] == "Aumento").sum()), "", "verde"),
        c.card("Reduções de limite", formatos.numero((df["tipo_alteracao"] == "Redução").sum()), "", "vermelho"),
        c.card("Reduções de prazo", formatos.numero(df["reducao_prazo"].sum()), "", "ambar"),
        c.card("Saldo das alterações", formatos.moeda_curta(df["alteracao_limite"].sum()), "soma de aumentos e reduções", "azul"),
    ]


PAGINAS = {
    "": Pagina(
        "", "Limite e prazo", "credito_clientes", "cliente_id",
        [c.coluna("cliente_id", "Cód.", largura=90, pinned="left"), c.coluna("fantasia", "Cliente", largura=210, pinned="left"),
         c.coluna("tipo_pessoa", "Tipo", largura=75), c.coluna("cidade", "Cidade", largura=125), c.coluna("canal", "Canal", largura=115),
         c.coluna("classificacao", "Classif.", largura=90), c.coluna("vendedor_id", "Vend.", largura=80),
         c.coluna("prazo_atual", "Prazo", largura=95), c.coluna("novo_prazo", "Novo prazo", largura=110, cellStyle=PRAZO_NOVO),
         c.coluna("debito_mais_antigo", "Venc. mais antigo (aberto)", "data", largura=190),
         c.coluna("dias_debito_antigo", "Dias vencido", "inteiro", largura=120, cellStyle=POSITIVO_RUIM),
         c.coluna("media_atraso", "Média atraso (dias)", "dec1", largura=150),
         c.coluna("faturamento_medio_3m", "Fat. médio 3M", "moeda", largura=130),
         c.coluna("limite_atual", "Limite atual", "moeda", largura=125), c.coluna("valor_aberto", "Em aberto", "moeda", largura=125),
         c.coluna("saldo_limite", "Saldo do limite", "moeda", largura=135, cellStyle=NEGATIVO),
         c.coluna("perc_limite_utilizado", "% usado", "pct", largura=100),
         c.coluna("sugestao_limite", "Sugestão de limite", largura=145),
         c.coluna("alteracao_limite", "Alteração", "moeda", largura=125, cellStyle=SINAL),
         c.coluna("qtd_reducoes_prazo", "Reduções de prazo", "inteiro", largura=145),
         c.coluna("qtd_solicitacoes", "Solicitações", "inteiro", largura=115)],
        {"cidade": "Cidade", "canal": "Canal", "classificacao": "Classificação", "vendedor_id": "Vendedor",
         "prazo_atual": "Prazo atual", "novo_prazo": "Novo prazo", "sugestao_limite": "Sugestão de limite",
         "limite_comprometido": "Limite comprometido"},
        _cards_inicio, ("media_atraso", False), detalhe_cliente=True),
    "cobranca": Pagina(
        "cobranca", "Cobrança", "credito_cobranca", "titulo_id",
        [c.coluna("cliente_id", "Cód.", largura=90, pinned="left"), c.coluna("fantasia", "Cliente", largura=210, pinned="left"),
         c.coluna("vendedor_atual", "Vend.", largura=80), c.coluna("vendedor_pedido", "Vend. pedido", largura=115),
         c.coluna("cidade", "Cidade", largura=125), c.coluna("canal", "Canal", largura=115), c.coluna("classificacao", "Classif.", largura=90),
         c.coluna("titulo_id", "Título", largura=95), c.coluna("pedido_id", "Pedido", largura=95),
         c.coluna("data_emissao", "Emissão", "data", largura=110), c.coluna("data_vencimento", "Vencimento", "data", largura=115),
         c.coluna("valor", "Valor", "moeda", largura=120), c.coluna("dias_atraso", "Dias de atraso", "inteiro", largura=120, cellStyle=POSITIVO_RUIM),
         c.coluna("faixa_atraso", "Faixa", largura=110), c.coluna("juros", "Juros", "moeda", largura=110, cellStyle=POSITIVO_RUIM),
         c.coluna("valor_atualizado", "Valor atualizado", "moeda", largura=140)],
        {"faixa_atraso": "Faixa de atraso", "vendedor_atual": "Vendedor", "cidade": "Cidade", "canal": "Canal", "classificacao": "Classificação"},
        _cards_cobranca, ("data_vencimento", True), detalhe_cliente=True),
    "solicitacoes": Pagina(
        "solicitacoes", "Solicitações", "credito_solicitacoes", "solicitacao_id",
        [c.coluna("solicitacao_id", "Nº", largura=80), c.coluna("data_solicitacao", "Data", "data", largura=110),
         c.coluna("cliente_id", "Cód.", largura=90), c.coluna("razao_social", "Cliente", largura=250),
         c.coluna("cidade", "Cidade", largura=125), c.coluna("classificacao", "Classif.", largura=90), c.coluna("tipo", "Tipo", largura=125),
         c.coluna("limite_atual", "Limite atual", "moeda", largura=125), c.coluna("limite_solicitado", "Limite pedido", "moeda", largura=130),
         c.coluna("prazo_atual", "Prazo atual", largura=110), c.coluna("prazo_solicitado", "Prazo pedido", largura=115, cellStyle=PRAZO_NOVO),
         c.coluna("media_atraso", "Média atraso", "dec1", largura=120), c.coluna("situacao", "Situação", largura=120, cellStyle=SITUACAO),
         c.coluna("solicitante", "Solicitante", largura=110), c.coluna("origem", "Origem", largura=95),
         c.coluna("observacao", "Observação", largura=280)],
        {"tipo": "Tipo", "situacao": "Situação", "solicitante": "Solicitante", "origem": "Origem", "cidade": "Cidade"},
        _cards_solicitacoes, ("data_solicitacao", False)),
    "historico": Pagina(
        "historico", "Histórico de implantações", "credito_historico", "cliente_id",
        [c.coluna("cliente_id", "Cód.", largura=90, pinned="left"), c.coluna("razao_social", "Cliente", largura=250, pinned="left"),
         c.coluna("cidade", "Cidade", largura=125), c.coluna("canal", "Canal", largura=115), c.coluna("classificacao", "Classif.", largura=90),
         c.coluna("prazo_antes", "Prazo antes", largura=110), c.coluna("prazo_depois", "Prazo depois", largura=115, cellStyle=PRAZO_NOVO),
         c.coluna("media_atraso", "Média atraso", "dec1", largura=120), c.coluna("faturamento_medio", "Faturamento médio", "moeda", largura=150),
         c.coluna("limite_antes", "Limite antes", "moeda", largura=125), c.coluna("limite_depois", "Limite depois", "moeda", largura=125),
         c.coluna("alteracao_limite", "Alteração", "moeda", largura=125, cellStyle=SINAL), c.coluna("tipo_alteracao", "Tipo", largura=100)],
        {"tipo_alteracao": "Tipo de alteração", "classificacao": "Classificação", "cidade": "Cidade", "prazo_depois": "Prazo depois"},
        _cards_historico, ("alteracao_limite", True), seletor="data_implantacao"),
}
