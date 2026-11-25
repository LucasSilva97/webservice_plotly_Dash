-- Comercial: a carteira fecha (ativos = cobertos + sem compra), a captação é novos - cancelados,
-- os percentuais somam 100 e toda revenda tem a meta própria (vendedor 0) em todo mês com venda.
select 'ruptura' as falha, revenda_id, mes, vendedor_id
from {{ ref('ruptura_vendedor_mes') }}
where clientes_ativos <> clientes_cobertos + clientes_sem_compra
   or captacao_liquida <> clientes_novos - clientes_cancelados
   or (clientes_ativos > 0 and abs(perc_cobertura + perc_ruptura - 100) > 0.011)

union all

select 'meta_revenda', v.revenda_id, v.mes, 0
from (select distinct revenda_id, mes from {{ ref('vendas_diarias') }}) as v
left join {{ ref('metas_mes') }} as m
    on m.revenda_id = v.revenda_id and m.mes = v.mes and m.vendedor_id = 0
where m.revenda_id is null
