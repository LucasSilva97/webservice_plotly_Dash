-- Grão: revenda x mês x vendedor da carteira.
-- Cobertura: cliente ativo no fechamento do mês com faturamento líquido > 0 no mês.
-- Ruptura = clientes ativos sem compra / clientes ativos.
-- Inadimplente: cliente ativo com título vencido há mais de dias_tolerancia_inadimplencia dias
-- e não pago no fechamento do mês (posição mês a mês, não só a de hoje).
-- Captação líquida = clientes novos - clientes bloqueados no mês.
with meses as (
    select mes, least(max(data), {{ data_referencia() }}) as fechamento
    from {{ ref('int_calendario') }}
    where data <= {{ data_referencia() }}
    group by mes
),

inadimplentes as (
    select distinct m.mes, t.cliente_id
    from {{ ref('stg_titulos_receber') }} as t
    inner join meses as m
        on t.data_vencimento + {{ var('dias_tolerancia_inadimplencia') }} < m.fechamento
       and (t.data_pagamento is null or t.data_pagamento > m.fechamento)
),

contagens as (
    select
        c.revenda_id,
        c.mes,
        c.vendedor_id,
        count(*) filter (where c.ativo_no_fechamento) as clientes_ativos,
        count(*) filter (where c.ativo_no_fechamento and f.valor_liquido > 0) as clientes_cobertos,
        count(*) filter (where c.ativo_no_fechamento and i.cliente_id is not null) as clientes_inadimplentes,
        count(*) filter (where c.novo_no_mes) as clientes_novos,
        count(*) filter (where c.bloqueado_no_mes) as clientes_cancelados
    from {{ ref('int_carteira_mensal') }} as c
    left join {{ ref('int_faturamento_cliente_mes') }} as f on f.cliente_id = c.cliente_id and f.mes = c.mes
    left join inadimplentes as i on i.cliente_id = c.cliente_id and i.mes = c.mes
    group by c.revenda_id, c.mes, c.vendedor_id
)

select
    c.revenda_id,
    c.mes,
    c.vendedor_id,
    v.vendedor,
    c.clientes_ativos,
    c.clientes_cobertos,
    c.clientes_ativos - c.clientes_cobertos as clientes_sem_compra,
    c.clientes_inadimplentes,
    c.clientes_novos,
    c.clientes_cancelados,
    c.clientes_novos - c.clientes_cancelados as captacao_liquida,
    round(100.0 * c.clientes_cobertos / nullif(c.clientes_ativos, 0), 2) as perc_cobertura,
    round(100.0 * (c.clientes_ativos - c.clientes_cobertos) / nullif(c.clientes_ativos, 0), 2) as perc_ruptura,
    round(100.0 * c.clientes_inadimplentes / nullif(c.clientes_ativos, 0), 2) as perc_inadimplencia
from contagens as c
left join {{ ref('stg_vendedores') }} as v on v.vendedor_id = c.vendedor_id
