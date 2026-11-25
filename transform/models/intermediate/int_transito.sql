-- Grão: documento x produto. Notas emitidas até a data de referência que ainda não deram
-- entrada no destino: compras vindas da fábrica e transferências entre unidades.
with compras as (
    select
        'Compra' as tipo,
        cast(nota_compra as varchar) as documento,
        revenda_id,
        fabricante as origem,
        produto_id,
        data_emissao,
        qtd_caixas
    from {{ ref('stg_compras_itens') }}
    where data_emissao <= {{ data_referencia() }}
      and (data_entrada is null or data_entrada > {{ data_referencia() }})
),

transferencias as (
    select
        'Transferência' as tipo,
        cast(t.nf_transferencia as varchar) as documento,
        t.revenda_destino as revenda_id,
        r.revenda as origem,
        t.produto_id,
        t.data_emissao,
        t.qtd_caixas
    from {{ ref('stg_transferencias') }} as t
    inner join {{ ref('stg_revendas') }} as r on r.revenda_id = t.revenda_origem
    where t.data_emissao <= {{ data_referencia() }}
      and (t.data_entrada is null or t.data_entrada > {{ data_referencia() }})
)

select
    *,
    date_diff('day', data_emissao, {{ data_referencia() }}) as dias_em_transito
from (select * from compras union all select * from transferencias)
