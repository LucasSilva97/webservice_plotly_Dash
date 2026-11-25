-- Grão: revenda x cliente x mês. Faturamento e volume líquidos do cliente no mês.
select
    revenda_id,
    cliente_id,
    mes,
    round(sum(valor_liquido), 2) as valor_liquido,
    sum(caixas_liquidas) as caixas_liquidas
from {{ ref('int_vendas_dia') }}
group by revenda_id, cliente_id, mes
