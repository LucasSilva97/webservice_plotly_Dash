-- Grão: revenda x data x vendedor (do pedido) x produto, somando os clientes.
-- Base do Diário de Vendas: faturamento e volume líquidos, com os atributos do produto.
select
    v.revenda_id,
    v.data,
    v.mes,
    v.vendedor_id,
    v.produto_id,
    p.produto,
    p.marca,
    p.fabricante,
    p.categoria,
    p.canal,
    sum(v.caixas_liquidas) as caixas_liquidas,
    sum(v.caixas_bonificadas) as caixas_bonificadas,
    round(sum(v.valor_liquido), 2) as valor_liquido
from {{ ref('int_vendas_dia') }} as v
inner join {{ ref('int_produtos_analise') }} as p on p.produto_id = v.produto_id
group by v.revenda_id, v.data, v.mes, v.vendedor_id, v.produto_id,
         p.produto, p.marca, p.fabricante, p.categoria, p.canal
