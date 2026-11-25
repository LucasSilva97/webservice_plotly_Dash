-- Grão: revenda x mês x cliente x vendedor (do pedido) x canal do produto.
-- Positivação = clientes distintos com faturamento líquido > 0. Como não se soma contagem
-- distinta, o painel conta os clientes deste mart depois de aplicar os filtros.
select
    v.revenda_id,
    v.mes,
    v.cliente_id,
    v.vendedor_id,
    p.canal,
    round(sum(v.valor_liquido), 2) as valor_liquido,
    sum(v.caixas_liquidas) as caixas_liquidas,
    sum(case when p.fabricante = '{{ var("fabricante_programa") }}' then v.caixas_liquidas else 0 end) as caixas_fabricante
from {{ ref('int_vendas_dia') }} as v
inner join {{ ref('int_produtos_analise') }} as p on p.produto_id = v.produto_id
group by v.revenda_id, v.mes, v.cliente_id, v.vendedor_id, p.canal
