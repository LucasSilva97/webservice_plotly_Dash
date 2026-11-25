-- Grão: nota de transferência x produto. Transferências que deram entrada na revenda depois da
-- última compra da fábrica: o estoque do produto veio de outra unidade desde então.
select
    t.revenda_destino as revenda_id,
    t.produto_id,
    t.nf_transferencia,
    r.revenda as origem,
    t.data_entrada,
    t.qtd_caixas
from {{ ref('stg_transferencias') }} as t
inner join {{ ref('stg_revendas') }} as r on r.revenda_id = t.revenda_origem
inner join {{ ref('int_produtos_analise') }} as p on p.produto_id = t.produto_id
left join {{ ref('int_ultima_compra') }} as uc
    on uc.revenda_id = t.revenda_destino and uc.produto_id = t.produto_id
where t.data_entrada <= {{ data_referencia() }}
  and (uc.ultima_compra is null or t.data_entrada > uc.ultima_compra)
