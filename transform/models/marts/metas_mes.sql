-- Grão: revenda x mês x vendedor. vendedor_id = 0 é a meta da revenda, definida à parte
-- (não é a soma das metas dos vendedores).
select
    m.revenda_id,
    m.mes,
    m.vendedor_id,
    coalesce(v.vendedor, 'Meta da revenda') as vendedor,
    m.meta_faturamento_imediato,
    m.meta_faturamento_abastecimento,
    m.meta_faturamento_imediato + m.meta_faturamento_abastecimento as meta_faturamento_total,
    m.meta_caixas_fabricante_imediato,
    m.meta_caixas_fabricante_abastecimento,
    m.meta_clientes_positivados
from {{ ref('int_metas') }} as m
left join {{ ref('stg_vendedores') }} as v on v.vendedor_id = m.vendedor_id
