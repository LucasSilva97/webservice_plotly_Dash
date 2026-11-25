"""Gera as fontes fictícias da Distribuidora Andorinha (empresa inventada).

Saída:
- data/fontes/erp.sqlite: o "ERP" (cadastros, pedidos, títulos, compras, transferências,
  estoque, contagens, solicitações e histórico de crédito);
- data/fontes/planilhas/metas_comerciais.csv: a planilha de metas do comercial, no formato
  pt-BR (separador ';', vírgula decimal e linhas de AJUSTE com sinal).

Todos os números, nomes e regras são inventados. A semente e a data de referência ficam em
elt/config.py: mesma semente + mesma data = mesmas fontes, byte a byte.

Os cenários que deixam as regras visíveis nos painéis estão marcados com "CENÁRIO".
"""
import csv
import sqlite3
from datetime import date, timedelta

import numpy as np
import pandas as pd

from elt import config

REF = config.DATA_REFERENCIA

REVENDAS = [
    # revenda_id, nome, cidade principal, cidade secundária, tipo
    (10, "Andorinha Centro", "Cidade Aurora", "Lagoa Mansa", "CD"),
    (20, "Andorinha Litoral", "Porto Sereno", "Praia Bonita", "FILIAL"),
    (30, "Andorinha Serra", "Serra Azulada", "Pedra Branca", "FILIAL"),
    (40, "Andorinha Vale", "Vale Dourado", "Campo Lindo", "FILIAL"),
]
FATOR_PRECO_REVENDA = {10: 1.00, 20: 1.03, 30: 0.98, 40: 1.01}

PRODUTOS = [
    # id, descrição, marca, fabricante, categoria, canal, unid/cx, litros/cx, custo, preço, popularidade, ativo
    (1001, "HORIZONTE PILSEN LATA 350ML CX12", "Horizonte", "Fábrica Horizonte", "Cerveja", "IMEDIATO", 12, 4.2, 28.0, 37.5, 10, 1),
    (1002, "HORIZONTE PILSEN GARRAFA 600ML CX24", "Horizonte", "Fábrica Horizonte", "Cerveja", "IMEDIATO", 24, 14.4, 95.0, 124.0, 9, 1),
    (1003, "HORIZONTE PILSEN LATA 350ML PACK18", "Horizonte", "Fábrica Horizonte", "Cerveja", "ABASTECIMENTO", 18, 6.3, 40.0, 52.0, 9, 1),
    (1004, "HORIZONTE PILSEN LATAO 473ML CX12", "Horizonte", "Fábrica Horizonte", "Cerveja", "ABASTECIMENTO", 12, 5.676, 38.0, 49.0, 7, 1),
    (1005, "HORIZONTE ZERO LATA 350ML CX12", "Horizonte Zero", "Fábrica Horizonte", "Cerveja", "IMEDIATO", 12, 4.2, 30.0, 40.0, 4, 1),
    (1006, "HORIZONTE ZERO LONG NECK 330ML CX24", "Horizonte Zero", "Fábrica Horizonte", "Cerveja", "IMEDIATO", 24, 7.92, 70.0, 92.0, 3, 1),
    (1007, "MARE ALTA PURO MALTE LONG NECK 330ML CX24", "Maré Alta", "Fábrica Horizonte", "Cerveja", "IMEDIATO", 24, 7.92, 88.0, 118.0, 6, 1),
    (1008, "MARE ALTA PURO MALTE LATA 350ML PACK12", "Maré Alta", "Fábrica Horizonte", "Cerveja", "ABASTECIMENTO", 12, 4.2, 36.0, 48.0, 5, 1),
    (1009, "MARE ALTA IPA LATA 350ML CX12", "Maré Alta", "Fábrica Horizonte", "Cerveja", "IMEDIATO", 12, 4.2, 42.0, 58.0, 2, 1),
    (1010, "MARE ALTA PURO MALTE GARRAFA 600ML CX24", "Maré Alta", "Fábrica Horizonte", "Cerveja", "IMEDIATO", 24, 14.4, 120.0, 158.0, 4, 1),
    (2001, "FONTE LUME AGUA SEM GAS 500ML CX12", "Fonte Lume", "Fábrica Lume", "Água", "IMEDIATO", 12, 6.0, 9.0, 14.0, 6, 1),
    (2002, "FONTE LUME AGUA COM GAS 500ML CX12", "Fonte Lume", "Fábrica Lume", "Água", "IMEDIATO", 12, 6.0, 10.0, 15.0, 3, 1),
    (2003, "FONTE LUME AGUA SEM GAS 1,5L CX6", "Fonte Lume", "Fábrica Lume", "Água", "ABASTECIMENTO", 6, 9.0, 10.0, 15.0, 4, 1),
    (2004, "CITRICA LIMAO LATA 350ML CX12", "Cítrica", "Fábrica Lume", "Refrigerante", "IMEDIATO", 12, 4.2, 22.0, 30.0, 5, 1),
    (2005, "CITRICA LARANJA LATA 350ML CX12", "Cítrica", "Fábrica Lume", "Refrigerante", "IMEDIATO", 12, 4.2, 22.0, 30.0, 4, 1),
    (2006, "CITRICA LIMAO PET 2L CX6", "Cítrica", "Fábrica Lume", "Refrigerante", "ABASTECIMENTO", 6, 12.0, 30.0, 41.0, 5, 1),
    (2007, "CITRICA LARANJA PET 2L CX6", "Cítrica", "Fábrica Lume", "Refrigerante", "ABASTECIMENTO", 6, 12.0, 30.0, 41.0, 4, 1),
    (2008, "CITRICA GUARANA PET 2L CX6", "Cítrica", "Fábrica Lume", "Refrigerante", "ABASTECIMENTO", 6, 12.0, 30.0, 41.0, 5, 1),
    # Fora da análise: produto descontinuado e material de ponto de venda (não é revenda).
    (2009, "CITRICA UVA PET 2L CX6 (DESCONTINUADO)", "Cítrica", "Fábrica Lume", "Refrigerante", "ABASTECIMENTO", 6, 12.0, 30.0, 41.0, 0, 0),
    (9001, "MESA PLASTICA PROMOCIONAL", "Material PDV", "Fábrica Horizonte", "Material PDV", "ABASTECIMENTO", 1, 0.0, 85.0, 0.0, 0, 1),
]
COLUNAS_PRODUTO = ["produto_id", "descricao", "marca", "fabricante", "categoria", "canal",
                   "unidades_por_caixa", "litros_por_caixa", "custo_base", "preco_base",
                   "popularidade", "ativo"]

CANAIS_CLIENTE = ["Bar", "Restaurante", "Mercado", "Conveniência", "Atacarejo"]
PESO_CANAIS = [0.35, 0.15, 0.25, 0.15, 0.10]
PREFERE_IMEDIATO = {"Bar": 0.85, "Restaurante": 0.75, "Mercado": 0.3, "Conveniência": 0.6, "Atacarejo": 0.2}
ADJETIVOS = ["Estrela", "Sol Nascente", "Bom Gosto", "Ponto Certo", "Boa Vista", "Primavera",
             "Esquina", "Encontro", "Farol", "Recanto", "Alvorada", "Mirante"]
BAIRROS = ["Centro", "Jardim das Flores", "Vila Nova", "Alto da Colina", "Beira Rio", "Parque Industrial"]

# Condições de pagamento (inventadas): id -> (descrição, dias)
CONDICOES = {1: ("À vista", 0), 2: ("7 dias", 7), 3: ("14 dias", 14), 4: ("21 dias", 21), 5: ("28 dias", 28)}
PESO_CONDICOES = [0.30, 0.25, 0.25, 0.15, 0.05]

# Escada de limites de crédito (inventada). O mart do crédito usa a mesma escada (dbt var).
ESCADA_LIMITE = [1500, 3000, 6000, 12000, 25000, 50000, 80000, 120000, 180000]

SAZONALIDADE = {1: 1.25, 2: 1.20, 3: 1.05, 4: 0.95, 5: 0.90, 6: 0.85,
                7: 0.85, 8: 0.90, 9: 0.95, 10: 1.00, 11: 1.10, 12: 1.35}
CRESCIMENTO_2026 = 1.07
CLIENTES_POR_REVENDA = 140

# CENÁRIO: a Litoral vende menos no mês corrente (menos pedidos e pedidos menores)
# -> tendência abaixo da meta no Diário e nas Metas.
QUEDA_LITORAL_MES_ATUAL = 0.82
# CENÁRIO: o vendedor 203 tem baixa positivação -> ruptura de carteira alta.
VENDEDOR_RUPTURA_ALTA = 203
# CENÁRIO: clientes que param de pagar -> limite comprometido, débito antigo e prazo à vista.
CLIENTES_INADIMPLENTES = [20007, 20015, 30022, 40031, 10044]


def _ler_feriados():
    caminho = config.PROJETO_DBT / "seeds" / "feriados.csv"
    return set(pd.read_csv(caminho, parse_dates=["data"])["data"].dt.date)


def dias_uteis(inicio, fim, feriados):
    """Segunda a sexta, menos os feriados do seed do dbt (mesma regra do int_calendario)."""
    return [d.date() for d in pd.date_range(inicio, fim, freq="D")
            if d.weekday() < 5 and d.date() not in feriados]


def degrau(valor):
    """Primeiro degrau da escada maior ou igual ao valor (o topo, se passar de todos)."""
    for limite in ESCADA_LIMITE:
        if valor <= limite:
            return limite
    return ESCADA_LIMITE[-1]


def _data_aleatoria(rng, inicio, fim):
    return inicio + timedelta(days=int(rng.integers(0, (fim - inicio).days + 1)))


def gerar_vendedores():
    linhas = []
    for revenda_id, *_ in REVENDAS:
        for k in range(1, 6):
            vendedor_id = revenda_id * 10 + k
            linhas.append((vendedor_id, revenda_id, f"Vendedor {vendedor_id}", 1))
    return pd.DataFrame(linhas, columns=["vendedor_id", "revenda_id", "nome", "ativo"])


def gerar_clientes(rng):
    """Cadastro + atributos ocultos de comportamento (tamanho, chance de compra, pagamento)."""
    linhas, historico = [], []
    for revenda_id, _, cidade1, cidade2, _ in REVENDAS:
        vendedores = [revenda_id * 10 + k for k in range(1, 6)]
        for i in range(1, CLIENTES_POR_REVENDA + 1):
            cliente_id = revenda_id * 1000 + i
            canal = str(rng.choice(CANAIS_CLIENTE, p=PESO_CANAIS))
            grande = canal == "Atacarejo" or (canal == "Mercado" and rng.random() < 0.15)
            tamanho = float(rng.lognormal(0, 0.4)) * (2.4 if canal == "Atacarejo" else 1.6 if grande else 1.0)
            adjetivo = ADJETIVOS[int(rng.integers(len(ADJETIVOS)))]
            pessoa_fisica = canal in ("Bar", "Conveniência") and rng.random() < 0.25

            if rng.random() < 0.85:
                cadastro = _data_aleatoria(rng, date(2018, 1, 1), date(2024, 12, 31))
            else:
                cadastro = _data_aleatoria(rng, date(2025, 1, 5), REF - timedelta(days=10))
            bloqueio = None
            if rng.random() < 0.07:
                inicio = max(cadastro + timedelta(days=60), date(2025, 2, 1))
                if inicio < REF - timedelta(days=3):
                    bloqueio = _data_aleatoria(rng, inicio, REF - timedelta(days=3))

            vendedor = int(rng.choice(vendedores))
            historico.append((cliente_id, vendedor, cadastro.isoformat()))
            if rng.random() < 0.10:  # troca de carteira no meio do período
                novo = int(rng.choice([v for v in vendedores if v != vendedor]))
                historico.append((cliente_id, novo, _data_aleatoria(rng, date(2025, 6, 1), date(2026, 10, 31)).isoformat()))

            condicao = int(rng.choice(list(CONDICOES), p=PESO_CONDICOES))
            perfil = str(rng.choice(["pontual", "atrasa_pouco", "atrasa_muito", "inadimplente"],
                                    p=[0.70, 0.18, 0.10, 0.02]))
            if cliente_id in CLIENTES_INADIMPLENTES:  # CENÁRIO: cliente antigo, ativo, que parou de pagar
                perfil, condicao, tamanho, bloqueio = "inadimplente", 4, max(tamanho, 2.5), None

            chance = float(rng.beta(1.8, 2.2))
            n_visitas = 2 if tamanho > 1.5 else 1
            dias_visita = sorted(int(x) for x in rng.choice(5, size=n_visitas, replace=False))
            linhas.append({
                "cliente_id": cliente_id, "revenda_id": revenda_id,
                "razao_social": (f"Cliente Pessoa Física {cliente_id}" if pessoa_fisica
                                 else f"{adjetivo} Comércio de Bebidas {i:03d} Ltda"),
                "fantasia": f"{canal} {adjetivo} {i:03d}",
                "tipo_pessoa": "PF" if pessoa_fisica else "PJ",
                "canal": canal, "classe": "Grandes Redes" if grande else "Regular",
                "cidade": cidade1 if rng.random() < 0.7 else cidade2,
                "bairro": BAIRROS[int(rng.integers(len(BAIRROS)))],
                "data_cadastro": cadastro.isoformat(),
                "data_bloqueio": bloqueio.isoformat() if bloqueio else None,
                "condicao_pagamento_id": condicao,
                # ocultos (não vão para o ERP)
                "_tamanho": tamanho, "_chance": chance, "_perfil": perfil, "_dias_visita": dias_visita,
            })
    clientes = pd.DataFrame(linhas)
    # Classificação de crédito pelo porte: A (15% maiores), B, C, D.
    quantis = clientes["_tamanho"].rank(pct=True, method="first")
    clientes["classificacao"] = np.select([quantis > 0.85, quantis > 0.60, quantis > 0.25], ["A", "B", "C"], "D")
    hist = pd.DataFrame(historico, columns=["cliente_id", "vendedor_id", "vigente_desde"])
    return clientes, hist


def _vendedor_na_data(hist_por_cliente, cliente_id, dia):
    vendedor = None
    for desde, vend in hist_por_cliente[cliente_id]:
        if desde <= dia:
            vendedor = vend
    return vendedor


def gerar_pedidos(rng, clientes, hist, feriados):
    """Pedidos (capa), itens, títulos a receber e devoluções, dia útil a dia útil."""
    produtos = pd.DataFrame(PRODUTOS, columns=COLUNAS_PRODUTO)
    vendaveis = produtos[(produtos["ativo"] == 1) & (produtos["popularidade"] > 0)].reset_index(drop=True)
    ids = vendaveis["produto_id"].to_numpy()
    imediato = (vendaveis["canal"] == "IMEDIATO").to_numpy()
    prob_por_canal = {}
    for canal, pref in PREFERE_IMEDIATO.items():
        peso = vendaveis["popularidade"].to_numpy() * np.where(imediato, pref, 1 - pref)
        prob_por_canal[canal] = peso / peso.sum()
    preco = dict(zip(vendaveis["produto_id"], vendaveis["preco_base"]))
    canal_produto = dict(zip(vendaveis["produto_id"], vendaveis["canal"]))

    hist_por_cliente = {}
    for c, v, desde in hist.sort_values(["cliente_id", "vigente_desde"]).itertuples(index=False):
        hist_por_cliente.setdefault(c, []).append((date.fromisoformat(desde), v))

    registros = clientes.to_dict("records")
    for c in registros:  # datas convertidas uma vez só (no DataFrame, o bloqueio vazio é NaN)
        c["_cadastro"] = date.fromisoformat(c["data_cadastro"])
        c["_bloqueio"] = date.fromisoformat(c["data_bloqueio"]) if isinstance(c["data_bloqueio"], str) else None
    capas, itens, titulos, devolucoes = [], [], [], []
    pedido_id, titulo_id, devolucao_id = 500000, 700000, 0
    for dia in dias_uteis(config.INICIO_HISTORICO, REF, feriados):
        sazonal = SAZONALIDADE[dia.month] * (CRESCIMENTO_2026 if dia.year == 2026 else 1.0)
        inflacao = 1.05 if dia.year == 2026 else 1.0
        mes_atual = (dia.year, dia.month) == (REF.year, REF.month)
        for c in registros:
            if dia.weekday() not in c["_dias_visita"]:
                continue
            if c["_cadastro"] > dia or (c["_bloqueio"] and c["_bloqueio"] <= dia):
                continue
            vendedor = _vendedor_na_data(hist_por_cliente, c["cliente_id"], dia)
            chance = c["_chance"]
            if vendedor == VENDEDOR_RUPTURA_ALTA:
                chance *= 0.30                      # CENÁRIO
            queda = QUEDA_LITORAL_MES_ATUAL if mes_atual and c["revenda_id"] == 20 else 1.0  # CENÁRIO
            chance *= queda
            if rng.random() >= chance:
                continue

            pedido_id += 1
            sorteio = rng.random()
            status = "CANCELADO" if sorteio < 0.03 else "FATURADO"
            if status == "CANCELADO" and (REF - dia).days <= 2:
                status = "BLOQUEADO"  # aguardando liberação de crédito
            n_itens = min(len(ids), 1 + int(rng.poisson(1.6 + 0.6 * min(c["_tamanho"], 3))))
            escolhidos = rng.choice(ids, size=n_itens, replace=False, p=prob_por_canal[c["canal"]])
            total = 0.0
            for item, produto_id in enumerate(sorted(int(p) for p in escolhidos), start=1):
                fator_canal = 1.0 if canal_produto[produto_id] == "IMEDIATO" else 0.8
                qtd = max(1, int(round(rng.gamma(2.0, 1.4) * c["_tamanho"] * sazonal * fator_canal * queda)))
                unitario = preco[produto_id] * FATOR_PRECO_REVENDA[c["revenda_id"]] * inflacao * (1 - rng.uniform(0, 0.06))
                valor = round(qtd * unitario, 2)
                total += valor
                itens.append((pedido_id, item, produto_id, "VENDA", qtd, valor))
                if status == "FATURADO" and rng.random() < 0.015:
                    data_dev = dia + timedelta(days=int(rng.integers(1, 6)))
                    if data_dev <= REF:
                        devolucao_id += 1
                        qtd_dev = int(rng.integers(1, qtd + 1))
                        devolucoes.append((devolucao_id, pedido_id, c["revenda_id"], c["cliente_id"], produto_id,
                                           data_dev.isoformat(), qtd_dev, round(valor * qtd_dev / qtd, 2)))
            if rng.random() < 0.04:  # bonificação: entra no volume, não no faturamento
                bonif = int(rng.choice(ids, p=prob_por_canal[c["canal"]]))
                itens.append((pedido_id, n_itens + 1, bonif, "BONIFICACAO", int(rng.integers(1, 3)), 0.0))
            capas.append((pedido_id, c["revenda_id"], c["cliente_id"], vendedor, dia.isoformat(),
                          c["condicao_pagamento_id"], status, round(total, 2)))

            dias_prazo = CONDICOES[c["condicao_pagamento_id"]][1]
            if status == "FATURADO" and dias_prazo > 0:
                vencimento = dia + timedelta(days=dias_prazo)
                perfil = c["_perfil"]
                if perfil == "pontual":
                    pagamento = max(dia, vencimento - timedelta(days=int(rng.integers(0, 3))))
                elif perfil == "atrasa_pouco":
                    pagamento = vencimento + timedelta(days=int(rng.integers(1, 7)))
                elif perfil == "atrasa_muito":
                    pagamento = vencimento + timedelta(days=int(rng.integers(6, 21)))
                else:  # inadimplente: parou de pagar há uns 75 dias
                    pagamento = None if dia >= REF - timedelta(days=75) else vencimento + timedelta(days=int(rng.integers(10, 31)))
                if pagamento is not None and pagamento > REF:
                    pagamento = None
                titulo_id += 1
                titulos.append((titulo_id, pedido_id, c["revenda_id"], c["cliente_id"], dia.isoformat(),
                                vencimento.isoformat(), round(total, 2),
                                pagamento.isoformat() if pagamento else None,
                                round(total, 2) if pagamento else 0.0))

    capas = pd.DataFrame(capas, columns=["pedido_id", "revenda_id", "cliente_id", "vendedor_id", "data_emissao",
                                         "condicao_pagamento_id", "status", "valor_total"])
    itens = pd.DataFrame(itens, columns=["pedido_id", "item", "produto_id", "tipo_item", "qtd_caixas", "valor"])
    titulos = pd.DataFrame(titulos, columns=["titulo_id", "pedido_id", "revenda_id", "cliente_id", "data_emissao",
                                             "data_vencimento", "valor", "data_pagamento", "valor_pago"])
    devolucoes = pd.DataFrame(devolucoes, columns=["devolucao_id", "pedido_id", "revenda_id", "cliente_id", "produto_id",
                                                   "data_devolucao", "qtd_caixas", "valor"])
    return capas, itens, titulos, devolucoes


def _vendas_por_mes(capas, itens):
    vendas = itens.merge(capas[capas["status"] == "FATURADO"], on="pedido_id")
    vendas["mes"] = vendas["data_emissao"].str[:7]
    return vendas


def gerar_compras(rng, vendas, feriados):
    """Notas de compra das fábricas: acompanham a venda do mês, com variação."""
    mensal = vendas.groupby(["revenda_id", "produto_id", "mes"], as_index=False)["qtd_caixas"].sum()
    produtos = pd.DataFrame(PRODUTOS, columns=COLUNAS_PRODUTO).set_index("produto_id")
    uteis = dias_uteis(config.INICIO_HISTORICO, REF, feriados)
    linhas, nota = [], 800000
    for r in mensal.sort_values(["revenda_id", "produto_id", "mes"]).itertuples(index=False):
        fator = rng.uniform(0.92, 1.08)
        if r.revenda_id == 40 and r.mes >= "2026-09":
            fator *= 1.25  # CENÁRIO: a Vale comprou demais -> sell-in acima do sell-out e estoque para reduzir
        total = int(round(r.qtd_caixas * fator))
        dias_mes = [d for d in uteis if d.isoformat()[:7] == r.mes]
        if total <= 0 or not dias_mes:
            continue
        if r.revenda_id == 20 and r.produto_id == 2003 and dias_mes[0] > REF - timedelta(days=70):
            continue  # CENÁRIO: última compra antiga
        partes = 3 if total >= 30 else 1
        for k, qtd in enumerate(np.array_split(np.arange(total), partes)):
            if len(qtd) == 0:
                continue
            emissao = dias_mes[int(rng.integers(len(dias_mes)))]
            entrada = emissao + timedelta(days=int(rng.integers(0, 2)))
            custo = produtos.loc[r.produto_id, "custo_base"] * (1.05 if emissao.year == 2026 else 1.0)
            nota += 1
            linhas.append((nota, r.revenda_id, produtos.loc[r.produto_id, "fabricante"], r.produto_id,
                           emissao.isoformat(), entrada.isoformat() if entrada <= REF else None,
                           len(qtd), round(len(qtd) * custo, 2)))
    return pd.DataFrame(linhas, columns=["nota_compra", "revenda_id", "fabricante", "produto_id",
                                         "data_emissao", "data_entrada", "qtd_caixas", "valor"])


def gerar_transferencias(rng, feriados):
    """Transferências do CD (revenda 10) para as filiais."""
    uteis = dias_uteis(config.INICIO_HISTORICO, REF, feriados)
    cervejas = [p[0] for p in PRODUTOS if p[4] == "Cerveja"]
    linhas, nf = [], 900000
    for destino in (20, 30, 40):
        for emissao in uteis[5 + destino // 10::15]:
            for produto_id in sorted(int(p) for p in rng.choice(cervejas, size=3, replace=False)):
                entrada = emissao + timedelta(days=int(rng.integers(1, 3)))
                nf += 1
                linhas.append((nf, 10, destino, produto_id, emissao.isoformat(),
                               entrada.isoformat() if entrada <= REF else None, int(rng.integers(20, 61))))
    # CENÁRIO: notas emitidas pelo CD que ainda não deram entrada no destino (em trânsito).
    for destino, produto_id, dias, qtd in [(30, 1001, 2, 80), (30, 1007, 2, 40), (20, 1002, 1, 60)]:
        nf += 1
        linhas.append((nf, 10, destino, produto_id, (REF - timedelta(days=dias)).isoformat(), None, qtd))
    # CENÁRIO: a Litoral está sem comprar água 1,5L da fábrica e recebeu do CD por transferência.
    for dias, qtd in [(25, 30), (12, 40)]:
        nf += 1
        linhas.append((nf, 10, 20, 2003, (REF - timedelta(days=dias)).isoformat(),
                       (REF - timedelta(days=dias - 2)).isoformat(), qtd))
    return pd.DataFrame(linhas, columns=["nf_transferencia", "revenda_origem", "revenda_destino", "produto_id",
                                         "data_emissao", "data_entrada", "qtd_caixas"])


def gerar_custos(rng):
    """Tabela de custo mensal por revenda e produto (o mart usa o mês mais recente)."""
    linhas = []
    meses = pd.period_range(config.INICIO_HISTORICO, REF, freq="M")
    for revenda_id, *_ in REVENDAS:
        for p in PRODUTOS:
            for mes in meses:
                if revenda_id == 40 and p[0] == 1009 and mes >= pd.Period("2026-10", "M"):
                    continue  # sem custo nos últimos meses: vale o último mês disponível
                custo = p[8] * (1.05 if mes.year == 2026 else 1.0) * FATOR_PRECO_REVENDA[revenda_id] * rng.uniform(0.99, 1.01)
                linhas.append((revenda_id, p[0], str(mes), round(custo, 2)))
    return pd.DataFrame(linhas, columns=["revenda_id", "produto_id", "mes", "custo_caixa"])


def gerar_estoque(rng, vendas, feriados):
    """Saldo do sistema na data de referência e a última contagem física de cada revenda."""
    inicio = REF - timedelta(days=30)
    n_uteis = len(dias_uteis(inicio, REF, feriados))
    recentes = vendas[vendas["data_emissao"] >= inicio.isoformat()]
    media = (recentes.groupby(["revenda_id", "produto_id"])["qtd_caixas"].sum() / n_uteis).to_dict()
    saldos = []
    for revenda_id, *_ in REVENDAS:
        for p in PRODUTOS:
            m = media.get((revenda_id, p[0]), 0.0)
            dias = rng.uniform(9, 17) if revenda_id == 10 else rng.uniform(6, 16)
            ajuste = {(20, 1002): 0, (20, 2004): 0, (20, 1005): 0,          # CENÁRIO: ruptura de estoque
                      (30, 1001): 2, (30, 1007): 1.5,                     # CENÁRIO: baixo, com trânsito
                      (40, 1003): 32, (40, 2006): 28, (40, 1008): 25}     # CENÁRIO: excesso
            dias = ajuste.get((revenda_id, p[0]), dias)
            saldo = int(round(m * dias))
            if p[0] in (2009, 9001):
                saldo = int(rng.integers(5, 20))  # fora da análise, mas existe no ERP
            saldos.append((revenda_id, p[0], REF.isoformat(), saldo))
    saldos = pd.DataFrame(saldos, columns=["revenda_id", "produto_id", "data_posicao", "saldo_caixas"])

    dias_contagem = {10: 3, 20: 6, 30: 2, 40: 8}
    divergencias = {(40, 1003): -40, (40, 2001): 12, (20, 1001): -15}  # CENÁRIO: contagem diferente do sistema
    contagens = saldos.copy()
    contagens["data_contagem"] = contagens["revenda_id"].map(lambda r: (REF - timedelta(days=dias_contagem[r])).isoformat())
    contagens["qtd_contada"] = [max(0, s + divergencias.get((r, p), 0))
                                for r, p, s in zip(contagens["revenda_id"], contagens["produto_id"], contagens["saldo_caixas"])]
    contagens = contagens[["revenda_id", "produto_id", "data_contagem", "qtd_contada"]]
    return saldos, contagens


def gerar_equipamentos(rng, clientes):
    linhas = []
    for c in clientes.itertuples(index=False):
        if c.canal in ("Bar", "Restaurante", "Conveniência"):
            if rng.random() < 0.6:
                linhas.append((c.cliente_id, "Geladeira vertical", int(rng.integers(1, 3))))
            if rng.random() < 0.3:
                linhas.append((c.cliente_id, "Freezer horizontal", 1))
            if rng.random() < 0.1:
                linhas.append((c.cliente_id, "Carrinho térmico", 1))
    return pd.DataFrame(linhas, columns=["cliente_id", "tipo_equipamento", "quantidade"])


def gerar_credito(rng, clientes, vendas):
    """Limite atual, histórico das implantações mensais e solicitações do portal de crédito."""
    inicio = (REF - timedelta(days=90)).isoformat()
    fat = vendas[vendas["data_emissao"] >= inicio].groupby("cliente_id")["valor"].sum() / 3
    clientes = clientes.copy()
    # Limite ~ compras do prazo x folga (o mart sugere com a mesma ideia e outra folga).
    clientes["limite_credito"] = [
        0.0 if c.condicao_pagamento_id == 1
        else float(degrau(fat.get(c.cliente_id, 0) * CONDICOES[c.condicao_pagamento_id][1] / 30 * rng.uniform(1.3, 2.0)))
        for c in clientes.itertuples(index=False)]

    historico = []
    a_prazo = clientes[(clientes["condicao_pagamento_id"] != 1) & clientes["data_bloqueio"].isna()]
    for mes in range(5, 12):
        data_implantacao = date(2026, mes, 5)
        for c in a_prazo.itertuples(index=False):
            if rng.random() >= 0.12:
                continue
            # O limite de hoje é o "depois"; o "antes" é o degrau vizinho (60% eram aumentos).
            depois = float(c.limite_credito)
            indice = ESCADA_LIMITE.index(depois)
            passo = indice - 1 if (rng.random() < 0.6 and indice > 0) else indice + 1
            antes = float(ESCADA_LIMITE[min(passo, len(ESCADA_LIMITE) - 1)])
            dias_antes = CONDICOES[c.condicao_pagamento_id][1]
            dias_depois = dias_antes if rng.random() < 0.8 else max(0, dias_antes - 7)
            historico.append((c.revenda_id, c.cliente_id, data_implantacao.isoformat(), c.classificacao,
                              dias_antes, dias_depois, round(float(rng.gamma(1.5, 2.0)), 1),
                              round(float(fat.get(c.cliente_id, 0)), 2), antes, depois))
    historico = pd.DataFrame(historico, columns=["revenda_id", "cliente_id", "data_implantacao", "classificacao",
                                                 "prazo_dias_antes", "prazo_dias_depois", "media_atraso",
                                                 "faturamento_medio", "limite_antes", "limite_depois"])
    observacoes = ["Cliente ampliou a loja", "Pedido maior para o fim de ano", "Revisão a pedido do vendedor",
                   "Cliente novo com bom histórico", "Ajuste de prazo pedido pelo cliente"]
    solicitacoes, sid = [], 0
    for _ in range(90):
        c = a_prazo.iloc[int(rng.integers(len(a_prazo)))]
        data = _data_aleatoria(rng, date(2026, 5, 20), REF)
        tipo = str(rng.choice(["Limite", "Prazo", "Limite e prazo"], p=[0.6, 0.2, 0.2]))
        situacao = "Em análise" if data > REF - timedelta(days=10) else str(rng.choice(["Aprovada", "Reprovada"], p=[0.7, 0.3]))
        dias_atual = CONDICOES[int(c.condicao_pagamento_id)][1]
        sid += 1
        solicitacoes.append((sid, int(c.revenda_id), int(c.cliente_id), data.isoformat(), tipo,
                             float(c.limite_credito),
                             float(degrau(c.limite_credito * 1.5)) if tipo != "Prazo" else None,
                             min(dias_atual + 7, 28) if tipo != "Limite" else None,
                             situacao, f"V{int(rng.integers(1, 6)) + int(c.revenda_id) * 10}",
                             observacoes[int(rng.integers(len(observacoes)))], "gerador"))
    solicitacoes = pd.DataFrame(solicitacoes, columns=[
        "solicitacao_id", "revenda_id", "cliente_id", "data_solicitacao", "tipo", "limite_atual",
        "limite_solicitado", "prazo_solicitado_dias", "situacao", "solicitante", "observacao", "origem"])
    return clientes, historico, solicitacoes


def _formata_br(valor, sinal=False):
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if sinal:
        return ("+" if valor >= 0 else "-") + texto
    return texto if valor >= 0 else "-" + texto


def gerar_metas(rng, capas, itens):
    """Planilha de metas: por revenda, mês e vendedor (0 = meta da revenda), em texto pt-BR."""
    produtos = pd.DataFrame(PRODUTOS, columns=COLUNAS_PRODUTO)[["produto_id", "canal", "fabricante"]]
    vendas = _vendas_por_mes(capas, itens).merge(produtos, on="produto_id")
    vendas["ano"] = vendas["mes"].str[:4].astype(int)
    vendas["m"] = vendas["mes"].str[5:].astype(int)
    vendas["fab"] = vendas["fabricante"] == "Fábrica Horizonte"

    def realizado(df):
        return {
            "FATURAMENTO_IMEDIATO": df.loc[df["canal"] == "IMEDIATO", "valor"].sum(),
            "FATURAMENTO_ABASTECIMENTO": df.loc[df["canal"] == "ABASTECIMENTO", "valor"].sum(),
            "CAIXAS_FABRICANTE_IMEDIATO": df.loc[df["fab"] & (df["canal"] == "IMEDIATO"), "qtd_caixas"].sum(),
            "CAIXAS_FABRICANTE_ABASTECIMENTO": df.loc[df["fab"] & (df["canal"] == "ABASTECIMENTO"), "qtd_caixas"].sum(),
            "CLIENTES_POSITIVADOS": df.loc[df["valor"] > 0, "cliente_id"].nunique(),
        }

    base = {chave: realizado(grupo) for chave, grupo in vendas.groupby(["revenda_id", "vendedor_id", "ano", "m"])}
    linhas = []
    for revenda_id, *_ in REVENDAS:
        vendedores = [revenda_id * 10 + k for k in range(1, 6)]
        for ano, mes in [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 13)]:
            totais = {}
            for vendedor in vendedores:
                if ano == 2025:
                    ref = base.get((revenda_id, vendedor, 2025, mes))
                    fatores = {k: rng.uniform(0.95, 1.06) for k in (ref or {})}
                else:
                    ref = base.get((revenda_id, vendedor, 2025, mes))
                    fatores = {k: (1.05 if k == "CLIENTES_POSITIVADOS" else 1.10) for k in (ref or {})}
                if not ref:
                    continue
                for tipo, valor in ref.items():
                    meta = round(valor * fatores[tipo]) if tipo.startswith(("CAIXAS", "CLIENTES")) else round(valor * fatores[tipo], -2)
                    totais[tipo] = totais.get(tipo, 0) + meta
                    linhas.append((revenda_id, f"{ano}-{mes:02d}", vendedor, tipo, "META", _formata_br(meta)))
            for tipo, soma in totais.items():  # a diretoria pede 2% acima da soma dos vendedores
                meta = round(soma * 1.02) if tipo.startswith(("CAIXAS", "CLIENTES")) else round(soma * 1.02, -2)
                linhas.append((revenda_id, f"{ano}-{mes:02d}", 0, tipo, "META", _formata_br(meta)))
    # Ajustes lançados à mão na planilha (somados à meta no intermediate).
    linhas.append((30, "2026-03", 0, "FATURAMENTO_IMEDIATO", "AJUSTE", _formata_br(5000, sinal=True)))
    linhas.append((20, "2026-07", 0, "FATURAMENTO_ABASTECIMENTO", "AJUSTE", _formata_br(-3000, sinal=True)))
    return linhas


def gravar(tabelas, metas):
    config.PASTA_PLANILHAS.mkdir(parents=True, exist_ok=True)
    temporario = config.ERP.with_suffix(".tmp")
    temporario.unlink(missing_ok=True)
    conexao = sqlite3.connect(temporario)  # o "with" do sqlite3 só faz commit; o close é explícito
    for nome, df in tabelas.items():
        df.to_sql(nome, conexao, index=False)
    conexao.close()
    temporario.replace(config.ERP)

    with open(config.PASTA_PLANILHAS / "metas_comerciais.csv", "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(["revenda", "mes", "vendedor", "tipo_meta", "tipo_linha", "valor"])
        escritor.writerows(metas)


def gerar():
    rng = np.random.default_rng(config.SEMENTE)
    feriados = _ler_feriados()
    vendedores = gerar_vendedores()
    clientes, hist = gerar_clientes(rng)
    capas, itens, titulos, devolucoes = gerar_pedidos(rng, clientes, hist, feriados)
    vendas = _vendas_por_mes(capas, itens)
    compras = gerar_compras(rng, vendas, feriados)
    transferencias = gerar_transferencias(rng, feriados)
    custos = gerar_custos(rng)
    saldos, contagens = gerar_estoque(rng, vendas, feriados)
    equipamentos = gerar_equipamentos(rng, clientes)
    clientes, historico, solicitacoes = gerar_credito(rng, clientes, vendas)
    metas = gerar_metas(rng, capas, itens)

    revendas = pd.DataFrame([(r[0], r[1], r[2], r[4]) for r in REVENDAS], columns=["revenda_id", "nome", "cidade", "tipo"])
    produtos = pd.DataFrame(PRODUTOS, columns=COLUNAS_PRODUTO).drop(columns=["custo_base", "preco_base", "popularidade"])
    condicoes = pd.DataFrame([(k, d, n) for k, (d, n) in CONDICOES.items()], columns=["condicao_pagamento_id", "descricao", "dias"])
    clientes = clientes.drop(columns=[c for c in clientes.columns if c.startswith("_")])

    tabelas = {
        "revendas": revendas, "vendedores": vendedores, "clientes": clientes,
        "clientes_vendedor_hist": hist, "condicoes_pagamento": condicoes, "produtos": produtos,
        "tabela_custos": custos, "pedidos": capas, "pedido_itens": itens, "devolucoes": devolucoes,
        "titulos_receber": titulos, "compras_itens": compras, "transferencias": transferencias,
        "estoque_saldos": saldos, "contagens_estoque": contagens, "equipamentos_cedidos": equipamentos,
        "solicitacoes_credito": solicitacoes, "historico_implantacoes": historico,
    }
    gravar(tabelas, metas)
    return {nome: len(df) for nome, df in tabelas.items()} | {"metas_comerciais.csv": len(metas)}


if __name__ == "__main__":
    for nome, linhas in gerar().items():
        print(f"{nome:28s} {linhas:>8,d}")
