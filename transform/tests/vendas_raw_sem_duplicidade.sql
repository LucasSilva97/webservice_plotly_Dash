-- Carga por janela: depois de qualquer número de reexecuções, a raw tem os mesmos pedidos e
-- itens que a fonte, sem duplicar. Os totais dos marts batem com os itens faturados.
with itens_faturados as (
    select sum(i.valor) as valor
    from {{ ref('stg_pedido_itens') }} as i
    inner join {{ ref('stg_pedidos') }} as p on p.pedido_id = i.pedido_id
    where p.status = 'FATURADO' and i.tipo_item = 'VENDA'
),

devolvido as (
    select sum(valor) as valor from {{ ref('stg_devolucoes') }}
),

mart as (
    select sum(valor_liquido) as valor from {{ ref('vendas_diarias') }}
)

select i.valor as itens, d.valor as devolucoes, m.valor as mart
from itens_faturados as i, devolvido as d, mart as m
where abs(i.valor - d.valor - m.valor) > 1
