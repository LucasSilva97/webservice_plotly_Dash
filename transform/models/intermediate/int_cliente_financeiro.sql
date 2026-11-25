-- Grão: cliente. Posição financeira na data de referência.
-- Média de atraso: títulos pagos na janela de dias (var credito_janela_dias); o vencimento que cai
-- no sábado ou no domingo só conta a partir da segunda-feira.
with abertos as (
    select
        cliente_id,
        sum(valor) as valor_aberto,
        sum(case when dias_atraso > 0 then valor else 0 end) as valor_vencido,
        min(data_vencimento) as vencimento_mais_antigo,
        max(dias_atraso) as dias_debito_antigo,
        max(semanas_atraso) as semanas_atraso
    from {{ ref('int_titulos_abertos') }}
    group by cliente_id
),

pagos as (
    select
        cliente_id,
        count(*) as qtd_titulos_pagos,
        avg(greatest(0, date_diff('day', vencimento_ajustado, data_pagamento))) as media_atraso
    from (
        select
            *,
            case isodow(data_vencimento)
                when 6 then data_vencimento + 2
                when 7 then data_vencimento + 1
                else data_vencimento
            end as vencimento_ajustado
        from {{ ref('stg_titulos_receber') }}
        where data_pagamento between {{ data_referencia() }} - {{ var('credito_janela_dias') }}
                                 and {{ data_referencia() }}
    )
    group by cliente_id
)

select
    c.cliente_id,
    round(coalesce(a.valor_aberto, 0), 2) as valor_aberto,
    round(coalesce(a.valor_vencido, 0), 2) as valor_vencido,
    a.vencimento_mais_antigo,
    coalesce(a.dias_debito_antigo, 0) as dias_debito_antigo,
    coalesce(a.semanas_atraso, 0) as semanas_atraso,
    coalesce(p.qtd_titulos_pagos, 0) as qtd_titulos_pagos,
    round(coalesce(p.media_atraso, 0), 1) as media_atraso
from {{ ref('stg_clientes') }} as c
left join abertos as a on a.cliente_id = c.cliente_id
left join pagos as p on p.cliente_id = c.cliente_id
