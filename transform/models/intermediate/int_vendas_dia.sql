-- Grão: revenda x data x cliente x vendedor x produto.
-- Volume líquido = vendido + bonificado - devolvido (a bonificação sai do estoque, mas não fatura).
-- Só pedidos FATURADO; a devolução entra na data em que aconteceu, com o vendedor do pedido.
with itens as (
    select
        p.revenda_id,
        p.data_emissao as data,
        p.cliente_id,
        p.vendedor_id,
        i.produto_id,
        case when i.tipo_item = 'VENDA' then i.qtd_caixas else 0 end as caixas_vendidas,
        case when i.tipo_item = 'BONIFICACAO' then i.qtd_caixas else 0 end as caixas_bonificadas,
        0 as caixas_devolvidas,
        case when i.tipo_item = 'VENDA' then i.valor else 0 end as valor_venda,
        0.0 as valor_devolvido
    from {{ ref('stg_pedido_itens') }} as i
    inner join {{ ref('stg_pedidos') }} as p on p.pedido_id = i.pedido_id
    where p.status = 'FATURADO'
),

devolucoes as (
    select
        d.revenda_id,
        d.data_devolucao as data,
        d.cliente_id,
        p.vendedor_id,
        d.produto_id,
        0 as caixas_vendidas,
        0 as caixas_bonificadas,
        d.qtd_caixas as caixas_devolvidas,
        0.0 as valor_venda,
        d.valor as valor_devolvido
    from {{ ref('stg_devolucoes') }} as d
    inner join {{ ref('stg_pedidos') }} as p on p.pedido_id = d.pedido_id
),

movimentos as (
    select * from itens
    union all
    select * from devolucoes
)

select
    revenda_id,
    data,
    {{ mes_int('data') }} as mes,
    cliente_id,
    vendedor_id,
    produto_id,
    sum(caixas_vendidas) as caixas_vendidas,
    sum(caixas_bonificadas) as caixas_bonificadas,
    sum(caixas_devolvidas) as caixas_devolvidas,
    sum(caixas_vendidas + caixas_bonificadas - caixas_devolvidas) as caixas_liquidas,
    round(sum(valor_venda), 2) as valor_venda,
    round(sum(valor_devolvido), 2) as valor_devolvido,
    round(sum(valor_venda - valor_devolvido), 2) as valor_liquido
from movimentos
where data <= {{ data_referencia() }}
group by revenda_id, data, cliente_id, vendedor_id, produto_id
