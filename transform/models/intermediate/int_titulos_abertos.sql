-- Grão: título. Títulos em aberto na data de referência, com o atraso em dias e em semanas.
with abertos as (
    select
        *,
        greatest(0, date_diff('day', data_vencimento, {{ data_referencia() }})) as dias_atraso
    from {{ ref('stg_titulos_receber') }}
    where data_emissao <= {{ data_referencia() }}
      and (data_pagamento is null or data_pagamento > {{ data_referencia() }})
)

select
    *,
    cast(ceil(dias_atraso / 7.0) as integer) as semanas_atraso,
    case
        when dias_atraso = 0 then 'A vencer'
        when ceil(dias_atraso / 7.0) >= 8 then '8+ semanas'
        when ceil(dias_atraso / 7.0) = 1 then '1 semana'
        else cast(cast(ceil(dias_atraso / 7.0) as integer) as varchar) || ' semanas'
    end as faixa_atraso
from abertos
