-- Grão: revenda x produto x mês. Sell-in (compras da fábrica, pela emissão da nota) contra
-- sell-out (volume líquido vendido), em caixas e em hectolitros.
with vendas as (
    select revenda_id, produto_id, mes, sum(caixas_liquidas) as caixas_vendidas
    from {{ ref('int_vendas_dia') }}
    group by revenda_id, produto_id, mes
),

compras as (
    select revenda_id, produto_id, {{ mes_int('data_emissao') }} as mes, sum(qtd_caixas) as caixas_compradas
    from {{ ref('stg_compras_itens') }}
    where data_emissao <= {{ data_referencia() }}
    group by revenda_id, produto_id, {{ mes_int('data_emissao') }}
),

chaves as (
    select revenda_id, produto_id, mes from vendas
    union
    select revenda_id, produto_id, mes from compras
)

select
    k.revenda_id,
    k.produto_id,
    k.mes,
    p.marca,
    coalesce(v.caixas_vendidas, 0) as caixas_vendidas,
    coalesce(c.caixas_compradas, 0) as caixas_compradas,
    round(coalesce(v.caixas_vendidas, 0) * p.litros_por_caixa / 100, 2) as hl_vendido,
    round(coalesce(c.caixas_compradas, 0) * p.litros_por_caixa / 100, 2) as hl_comprado
from chaves as k
inner join {{ ref('int_produtos_analise') }} as p on p.produto_id = k.produto_id
left join vendas as v on v.revenda_id = k.revenda_id and v.produto_id = k.produto_id and v.mes = k.mes
left join compras as c on c.revenda_id = k.revenda_id and c.produto_id = k.produto_id and c.mes = k.mes
