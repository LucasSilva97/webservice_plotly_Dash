-- Grão: título em aberto na data de referência (a vencer ou vencido).
-- Juros simples: valor x credito_juros_dia x dias de atraso, sem teto.
select
    t.titulo_id,
    t.pedido_id,
    t.revenda_id,
    r.revenda,
    t.cliente_id,
    c.razao_social,
    c.fantasia,
    c.cidade,
    c.canal,
    c.classificacao,
    va.vendedor_id as vendedor_atual,
    p.vendedor_id as vendedor_pedido,
    t.data_emissao,
    t.data_vencimento,
    t.valor,
    t.dias_atraso,
    t.semanas_atraso,
    t.faixa_atraso,
    round(t.valor * {{ var('credito_juros_dia') }} * t.dias_atraso, 2) as juros,
    round(t.valor * (1 + {{ var('credito_juros_dia') }} * t.dias_atraso), 2) as valor_atualizado
from {{ ref('int_titulos_abertos') }} as t
inner join {{ ref('stg_clientes') }} as c on c.cliente_id = t.cliente_id
inner join {{ ref('stg_revendas') }} as r on r.revenda_id = t.revenda_id
left join {{ ref('stg_pedidos') }} as p on p.pedido_id = t.pedido_id
left join {{ ref('int_cliente_vendedor_atual') }} as va on va.cliente_id = t.cliente_id
